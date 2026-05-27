import time

from langgraph.graph import END, START, StateGraph
from rich import print

from core.io import (
    AVAILABLE_STEPS,
    ensure_logbook_dir,
    get_step_prompt,
    prepare_step_input,
    write_step_json,
)
from core.llm_steps import invoke_step
from core.state import FRState
from core.status import set_fr_status

fr_graph = None


def _route_after_step(state: FRState) -> str:
    if state.get("error"):
        return END
    step = state.get("current_step", 0)
    if step >= 8:
        return END
    return f"step{step + 1}"


def execute_step(
    pdf_name: str,
    fr_id: str,
    fr_text: str,
    step_number: int,
    step_outputs: dict | None = None,
) -> dict:
    """Run one step; returns state updates (step_outputs, current_step, error)."""
    print(f"\nProcessing step {step_number} for {pdf_name} - {fr_id}")
    set_fr_status(
        pdf_name,
        fr_id,
        step_number,
        "running",
        f"Step {step_number}/8",
    )

    step_prompt = get_step_prompt(step_number)
    step_input_data = prepare_step_input(pdf_name, fr_id, fr_text, step_number)
    overall_start = time.time()

    try:
        llm_response = invoke_step(
            step_number, step_prompt, step_input_data, fr_text
        )
        write_step_json(
            pdf_name,
            fr_id,
            fr_text,
            step_number,
            step_prompt,
            step_input_data,
            llm_response=llm_response,
        )
        elapsed = time.time() - overall_start
        print(f"Completed step {step_number} for {fr_id} in {elapsed:.1f}s")

        phase = "done" if step_number == 8 else "running"
        set_fr_status(
            pdf_name,
            fr_id,
            step_number,
            phase,
            f"Step {step_number}/8 complete",
        )

        outputs = dict(step_outputs or {})
        outputs[step_number] = llm_response
        return {
            "step_outputs": outputs,
            "current_step": step_number,
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - overall_start
        print(f"Error in step {step_number} for {fr_id}: {e} ({elapsed:.1f}s)")
        write_step_json(
            pdf_name,
            fr_id,
            fr_text,
            step_number,
            step_prompt,
            step_input_data,
            error=str(e),
        )
        set_fr_status(pdf_name, fr_id, step_number, "error", str(e))
        return {"error": str(e), "current_step": step_number}


def _make_step_node(step_number: int):
    def node(state: FRState) -> dict:
        if state.get("error"):
            return {}
        return execute_step(
            state["pdf_name"],
            state["fr_id"],
            state["fr_text"],
            step_number,
            state.get("step_outputs"),
        )

    return node


def build_fr_graph():
    builder = StateGraph(FRState)
    for n in AVAILABLE_STEPS:
        builder.add_node(f"step{n}", _make_step_node(n))

    builder.add_edge(START, "step1")
    for n in range(1, 8):
        builder.add_conditional_edges(f"step{n}", _route_after_step)
    builder.add_edge("step8", END)

    return builder.compile()


def get_fr_graph():
    global fr_graph
    if fr_graph is None:
        fr_graph = build_fr_graph()
    return fr_graph


def run_fr_pipeline(pdf_name: str, fr: dict[str, str], steps: list[int] | None = None) -> FRState:
    """Run the pipeline for a single FR (full graph or selected steps)."""
    fr_id = list(fr.keys())[0]
    fr_text = fr[fr_id]
    ensure_logbook_dir(pdf_name, fr_id)

    if steps is None or steps == AVAILABLE_STEPS:
        initial: FRState = {
            "pdf_name": pdf_name,
            "fr_id": fr_id,
            "fr_text": fr_text,
            "step_outputs": {},
            "current_step": 0,
            "error": None,
        }
        return get_fr_graph().invoke(initial)

    step_outputs: dict = {}
    error = None
    for step_num in steps:
        if step_num not in AVAILABLE_STEPS:
            print(f"Warning: Step {step_num} is not available. Skipping.")
            continue
        result = execute_step(
            pdf_name, fr_id, fr_text, step_num, step_outputs
        )
        step_outputs = result.get("step_outputs", step_outputs)
        error = result.get("error")
        if error:
            break

    return {
        "pdf_name": pdf_name,
        "fr_id": fr_id,
        "fr_text": fr_text,
        "current_step": max(steps) if steps else 0,
        "error": None,
    }
