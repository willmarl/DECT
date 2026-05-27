from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from rich import print

from core.fr_graph import get_fr_graph
from core.state import BatchState, FRState
from core.status import set_fr_status, write_pipeline_status


def _run_fr_pipeline(state: FRState) -> dict:
    """Run one FR subgraph; return only reducer-safe batch updates."""
    get_fr_graph().invoke(state)
    return {"completed_frs": [state["fr_id"]]}


def _dispatch_frs(state: BatchState) -> list[Send]:
    pdf_name = state["pdf_name"]
    sends = []
    for fr in state["frs"]:
        fr_id = list(fr.keys())[0]
        fr_text = fr[fr_id]
        fr_state: FRState = {
            "pdf_name": pdf_name,
            "fr_id": fr_id,
            "fr_text": fr_text,
            "step_outputs": {},
            "current_step": 0,
            "error": None,
        }
        sends.append(Send("fr_pipeline", fr_state))
    return sends


def build_batch_graph():
    builder = StateGraph(BatchState)
    builder.add_node("fr_pipeline", _run_fr_pipeline)
    builder.add_conditional_edges(START, _dispatch_frs, ["fr_pipeline"])
    builder.add_edge("fr_pipeline", END)
    return builder.compile()


_batch_graph = None


def get_batch_graph():
    global _batch_graph
    if _batch_graph is None:
        _batch_graph = build_batch_graph()
    return _batch_graph


def run_batch_pipeline(pdf_name: str, frs_list: list[dict[str, str]]) -> None:
    """Run all FRs for a PDF in parallel (capped by MAX_PARALLEL_FRS at LLM layer)."""
    if not frs_list:
        return

    for fr in frs_list:
        fr_id = list(fr.keys())[0]
        set_fr_status(pdf_name, fr_id, 0, "running", "Queued")

    write_pipeline_status(
        f"Starting analysis of {pdf_name} with {len(frs_list)} FRs (parallel)"
    )
    print(f"\n=== Starting parallel pipeline for {pdf_name} ({len(frs_list)} FRs) ===")

    get_batch_graph().invoke({
        "pdf_name": pdf_name,
        "frs": frs_list,
        "completed_frs": [],
    })

    print(f"\n=== Completed parallel pipeline for {pdf_name} ===")
    write_pipeline_status(
        f"Analysis complete! Processed {len(frs_list)} FRs for {pdf_name}"
    )
