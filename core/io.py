import json
from pathlib import Path

import utils.prompts as prompts

AVAILABLE_STEPS = [1, 2, 3, 4, 5, 6, 7, 8]


def pdf_stem(pdf_name: str) -> str:
    return Path(pdf_name).stem


def logbook_dir(pdf_name: str, fr_id: str) -> Path:
    return Path(f"data/pdf_logbook/{pdf_stem(pdf_name)}/{fr_id}")


def step_file_path(pdf_name: str, fr_id: str, step_number: int) -> Path:
    return logbook_dir(pdf_name, fr_id) / f"step{step_number}.json"


def ensure_logbook_dir(pdf_name: str, fr_id: str) -> Path:
    directory = logbook_dir(pdf_name, fr_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def read_step_json(pdf_name: str, fr_id: str, step_number: int) -> dict | None:
    path = step_file_path(pdf_name, fr_id, step_number)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def prepare_step_input(pdf_name: str, fr_id: str, fr_text: str, step_number: int) -> dict:
    """Prepare input data for a step from the previous step output on disk."""
    if step_number == 1:
        return {"requirement_text": fr_text}

    prev_data = read_step_json(pdf_name, fr_id, step_number - 1)
    if prev_data:
        if "llm_response" in prev_data:
            return prev_data["llm_response"]
        if "input_data" in prev_data:
            return prev_data["input_data"]

    return {"requirement_text": fr_text}


def write_step_json(
    pdf_name: str,
    fr_id: str,
    fr_text: str,
    step_number: int,
    step_prompt: dict,
    step_input_data: dict,
    llm_response: dict | None = None,
    error: str | None = None,
) -> Path:
    ensure_logbook_dir(pdf_name, fr_id)
    path = step_file_path(pdf_name, fr_id, step_number)
    output_data: dict = {
        "prompt": step_prompt,
        "input_data": step_input_data,
        "fr_id": fr_id,
        "fr_text": fr_text,
        "step_number": step_number,
    }
    if error:
        output_data["error"] = error
    else:
        output_data["llm_response"] = llm_response

    path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    return path


def get_step_prompt(step_number: int) -> dict:
    if step_number not in AVAILABLE_STEPS:
        raise ValueError(
            f"Step {step_number} is not available. Available steps: {AVAILABLE_STEPS}"
        )
    return getattr(prompts, f"STEP{step_number}")
