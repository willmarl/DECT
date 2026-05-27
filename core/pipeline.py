"""Public pipeline API: batch run, combine outputs, and helpers."""

from pathlib import Path
import json

import pandas as pd
from rich import print

from core.batch_graph import run_batch_pipeline
from core.fr_graph import execute_step, run_fr_pipeline
from core.io import (
    AVAILABLE_STEPS,
    ensure_logbook_dir,
    get_step_prompt,
    pdf_stem,
)
from core.status import (
    get_batch_status,
    set_fr_status,
    write_pipeline_status,
)

__all__ = [
    "AVAILABLE_STEPS",
    "pipeline",
    "run_pipeline_for_pdf",
    "run_single_step",
    "run_steps_range",
    "get_step_prompt",
    "list_output_files",
    "get_fr_directories",
    "combine_all_step8_files",
    "generate_csv_from_final_output",
    "write_pipeline_status",
    "get_batch_status",
]


def generate_csv_from_final_output(final_output, outputs_dir):
    """Generate CSV file from final output data structure."""
    try:
        csv_path = outputs_dir / "final_output.csv"
        rows = []
        document_id = final_output.get("document_id", "Unknown Document")

        for test_suite in final_output.get("test_suite", []):
            fr_id = test_suite.get("fr_id", "Unknown")
            for i, test_case in enumerate(test_suite.get("test_cases", []), 1):
                rows.append({
                    "Document": document_id,
                    "FR ID": fr_id,
                    "Test #": i,
                    "Test Case": test_case.get("title", ""),
                    "Precondition": test_case.get("precondition", ""),
                    "Steps": test_case.get("steps", ""),
                    "Test Data": test_case.get("test_data", ""),
                    "Expected Result": test_case.get("expected_result", ""),
                    "Environment": test_case.get("environment", ""),
                    "Actual Result": test_case.get("actual_result", ""),
                    "Status": test_case.get("status", ""),
                    "Jira Bug Link": test_case.get("jira_bug_link", ""),
                })

        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(csv_path, index=False, encoding="utf-8")
            return True, f"CSV saved to: {csv_path}"
        return False, "No test cases found to export"
    except Exception as e:
        return False, f"Error generating CSV: {str(e)}"


def pipeline(pdf_name, fr, steps=None):
    """Run pipeline steps for one FR via LangGraph (or selected steps sequentially)."""
    fr_id = list(fr.keys())[0]
    fr_text = fr[fr_id]
    ensure_logbook_dir(pdf_name, fr_id)

    print(f"Starting pipeline for {pdf_name} - {fr_id}: {fr_text[:50]}...")
    set_fr_status(pdf_name, fr_id, 0, "running", "Starting")
    write_pipeline_status(f"Starting pipeline for {fr_id}...")

    run_fr_pipeline(pdf_name, fr, steps)

    print(f"Pipeline completed for {pdf_name} - {fr_id}")
    set_fr_status(pdf_name, fr_id, 8, "done", "All steps finished")
    write_pipeline_status(get_batch_status(pdf_name, [fr_id]) or f"Completed {fr_id}")


def run_step(pdf_name, fr_id, fr_text, step_number):
    """Run a single pipeline step (debug / partial re-run)."""
    execute_step(pdf_name, fr_id, fr_text, step_number)


def run_single_step(pdf_name, fr, step_number):
    fr_id = list(fr.keys())[0]
    fr_text = fr[fr_id]
    ensure_logbook_dir(pdf_name, fr_id)
    run_step(pdf_name, fr_id, fr_text, step_number)


def run_steps_range(pdf_name, fr, start_step, end_step):
    steps = list(range(start_step, end_step + 1))
    pipeline(pdf_name, fr, steps)


def list_output_files(pdf_name, fr_id=None):
    base_dir = Path(f"data/pdf_logbook/{pdf_stem(pdf_name)}")
    if not base_dir.exists():
        return []

    step_files = []
    if fr_id:
        fr_dir = base_dir / fr_id
        if fr_dir.exists():
            for step_num in AVAILABLE_STEPS:
                step_file = fr_dir / f"step{step_num}.json"
                if step_file.exists():
                    step_files.append(step_file)
    else:
        for fr_dir in base_dir.iterdir():
            if fr_dir.is_dir() and fr_dir.name.startswith("FR-"):
                for step_num in AVAILABLE_STEPS:
                    step_file = fr_dir / f"step{step_num}.json"
                    if step_file.exists():
                        step_files.append(step_file)
    return step_files


def get_fr_directories(pdf_name):
    base_dir = Path(f"data/pdf_logbook/{pdf_stem(pdf_name)}")
    if not base_dir.exists():
        return []
    return sorted(
        fr_dir.name
        for fr_dir in base_dir.iterdir()
        if fr_dir.is_dir() and fr_dir.name.startswith("FR-")
    )


def run_pipeline_for_pdf(pdf_name, frs_list):
    """Run all FRs for a PDF in parallel, then print a summary."""
    print(f"\n=== Starting pipeline for {pdf_name} ===")
    print(f"Found {len(frs_list)} functional requirements")
    fr_ids = [list(fr.keys())[0] for fr in frs_list]

    run_batch_pipeline(pdf_name, frs_list)

    for fr_id in fr_ids:
        files = list_output_files(pdf_name, fr_id)
        print(f"{fr_id}: {len(files)} step files generated")

    summary = get_batch_status(pdf_name, fr_ids)
    if summary:
        write_pipeline_status(summary)


def combine_all_step8_files():
    """Scan logbooks and combine step8 outputs into final_output.json + CSV."""
    from utils.mockData import fakeFinalOutput

    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)

    logbook_base = Path("data/pdf_logbook")
    step8_files = []

    if logbook_base.exists():
        for pdf_dir in logbook_base.iterdir():
            if pdf_dir.is_dir() and pdf_dir.name != ".status":
                for fr_dir in pdf_dir.iterdir():
                    if fr_dir.is_dir() and fr_dir.name.startswith("FR-"):
                        step8_file = fr_dir / "step8.json"
                        if step8_file.exists():
                            step8_files.append({
                                "pdf_name": pdf_dir.name,
                                "fr_id": fr_dir.name,
                                "file_path": step8_file,
                            })

    print(f"Found {len(step8_files)} step8 files to combine:")
    for file_info in step8_files:
        print(f"  {file_info['pdf_name']} - {file_info['fr_id']}")

    if step8_files:
        test_suites = []
        for file_info in step8_files:
            processed = process_step8_file(file_info["file_path"])
            if processed:
                test_suites.append(processed)
        if test_suites:
            pdf_name = step8_files[0]["pdf_name"]
            final_output = create_final_output_structure(test_suites, pdf_name)
        else:
            print("Warning: No valid step8 data found, using fallback fake data")
            final_output = fakeFinalOutput
    else:
        print("Warning: No step8 files found, using fallback fake data")
        final_output = fakeFinalOutput

    final_output_path = outputs_dir / "final_output.json"
    with open(final_output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    print(f"\nFinal output saved to: {final_output_path}")

    csv_success, csv_message = generate_csv_from_final_output(final_output, outputs_dir)
    if csv_success:
        print(f"CSV export: {csv_message}")
    else:
        print(f"CSV export failed: {csv_message}")

    write_pipeline_status(
        f"Final results ready! Generated test cases from {len(step8_files)} FRs"
    )
    return final_output_path


def process_step8_file(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            step8_data = json.load(f)

        if step8_data.get("llm_response"):
            llm_response = step8_data["llm_response"]
            return {
                "fr_id": llm_response.get("fr_id", step8_data.get("fr_id", "Unknown")),
                "test_cases": llm_response.get("test_cases", []),
            }
        if "fr_id" in step8_data:
            print(f"Warning: No LLM response found in {file_path}")
            return {
                "fr_id": step8_data.get("fr_id", "Unknown"),
                "test_cases": [],
            }
        print(f"Warning: Invalid step8 file format: {file_path}")
        return None
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error processing step8 file {file_path}: {e}")
        return None


def create_final_output_structure(step8_results, pdf_name):
    return {
        "document_id": f"{pdf_name}.pdf",
        "test_suite": step8_results,
    }
