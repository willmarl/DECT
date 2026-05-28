import gradio as gr
import pandas as pd
from io import StringIO
from components.taskSelector import create_task_selector
from components.ui_styles import RESULTS_COLUMN_WIDTHS
from downloads.dataframe import load_final_output_as_dataframe
from downloads.ensure import get_csv_download_path, get_json_download_path
from downloads.paths import results_download_available
from time import sleep
from pathlib import Path
import threading
import time
import subprocess
import signal
import os

# Global variable to track running processes
current_process = {}

def get_status_outputs():
    """Return (simple_markdown, detail_log) for the status UI."""
    from core.status import get_status_ui
    return get_status_ui()


STATUS_READY_SIMPLE = "✅ Ready — upload a PDF to begin"
STATUS_READY_LOG = "No activity yet."
SAVED_PDFS_EMPTY = (
    "No processed PDFs saved yet.\n\n"
    'Upload a PDF and click "1. Process PDF".'
)


def format_saved_processed_pdfs() -> str:
    """List PDFs with extracted requirements still on disk (survives page refresh)."""
    json_dir = Path("data/extractedFR")
    if not json_dir.is_dir():
        return SAVED_PDFS_EMPTY
    names = sorted(p.stem for p in json_dir.glob("*.json"))
    if not names:
        return SAVED_PDFS_EMPTY
    lines = "\n".join(f"• {name}.pdf" for name in names)
    return f"Still saved on disk ({len(names)}):\n\n{lines}"

def isButtonValid(x):
    if x is not None and len(x) > 0:
        return gr.update(interactive=True)
    else:
        return gr.update(interactive=False)


def download_buttons_update(interactive: bool):
    """Enable or disable both download buttons together."""
    if interactive:
        return gr.update(interactive=True), gr.update(interactive=True)
    return gr.update(interactive=False, value=None), gr.update(interactive=False, value=None)


def download_buttons_state() -> tuple:
    """Download button state and file paths (pre-set value = one-click download)."""
    proc = current_process.get("process")
    if proc is not None and proc.poll() is None:
        return download_buttons_update(False)

    if not results_download_available():
        return download_buttons_update(False)

    json_path = get_json_download_path()
    csv_path = get_csv_download_path()
    if not json_path:
        return download_buttons_update(False)

    return (
        gr.update(interactive=True, value=json_path),
        gr.update(interactive=True, value=csv_path) if csv_path else gr.update(interactive=False),
    )


def on_files_uploaded(files):
    """Enable Process PDF and show a simple received message (not processing yet)."""
    from core.status import clear_app_status, note_files_uploaded
    import os

    btn = isButtonValid(files)
    if not files:
        clear_app_status()
        return btn, STATUS_READY_SIMPLE, STATUS_READY_LOG
    names = [os.path.basename(f.name) for f in files]
    note_files_uploaded(names)
    simple, detail = get_status_outputs()
    return btn, simple, detail

# Note: updateRunButton and processPdfAndUpdateButton functions have been replaced 
# with the inline process_pdf_and_refresh function in the top() function

def _start_pipeline_subprocess(max_parallel: int):
    """Start pipeline subprocess; caller must poll and call _finish_pipeline_subprocess."""
    import sys
    from core.concurrency import set_max_parallel_frs
    from core.status import set_app_status, append_status_log

    parallel = set_max_parallel_frs(max_parallel)
    set_app_status(
        "pipeline",
        "Starting test pipeline",
        f"Up to {parallel} FR(s) at once (parallel LLM calls)",
        active=True,
        simple=f"🚀 Starting pipeline — {parallel} parallel FR(s)",
    )
    append_status_log("Subprocess: python -m core.simple_run")
    append_status_log(f"Parallel FR limit: {parallel}")

    env = os.environ.copy()
    env["MAX_PARALLEL_FRS"] = str(parallel)

    process = subprocess.Popen(
        [sys.executable, "-m", "core.simple_run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path.cwd(),
        env=env,
    )
    current_process["process"] = process
    current_process["type"] = "pipeline"
    return process


def _finish_pipeline_subprocess(process):
    """Wait for pipeline process and return (success, status_message)."""
    from core.status import set_app_status, get_status_ui

    stdout, stderr = process.communicate()
    current_process["process"] = None
    current_process["type"] = None

    if process.returncode == 0:
        set_app_status(
            "idle",
            "Pipeline completed successfully",
            "See results below",
            active=False,
            simple="📥 Results ready for download",
        )
        simple, _detail = get_status_ui()
        return True, f"{simple}\n\n📥 Download JSON + CSV below."
    if process.returncode in (-signal.SIGTERM, -signal.SIGKILL):
        set_app_status(
            "idle", "Pipeline stopped", "Stopped by user", active=False, simple="🛑 Stopped"
        )
        return False, "🛑 Pipeline analysis was stopped by user"
    set_app_status(
        "error",
        "Pipeline failed",
        stderr[:500] if stderr else "Unknown error",
        active=False,
        simple="❌ Pipeline failed",
    )
    return False, f"❌ Pipeline failed:\n{stderr}"

def checkTaskSelection(selection_status):
    """Check if tasks are selected to enable/disable run button"""
    is_selected = selection_status == "True"
    return gr.update(interactive=is_selected)

def stop_current_process():
    """Stop pipeline subprocess or in-thread PDF processing.

    Returns (message, kind) where kind is \"pdf\", \"pipeline\", or None.
    """
    from core.status import (
        append_status_log,
        is_pdf_processing_active,
        request_pdf_cancel,
        set_app_status,
    )

    if is_pdf_processing_active():
        request_pdf_cancel()
        append_status_log("PDF process stopped by user")
        set_app_status(
            "idle",
            "PDF processing stopped",
            "Stopped by user",
            active=False,
            simple="🛑 Stopped",
        )
        return "🛑 Stopped", "pdf"

    if current_process.get("process") and current_process.get("type"):
        try:
            process = current_process["process"]
            process_type = current_process["type"]

            if os.name == "nt":
                process.terminate()
            else:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

            current_process.clear()

            append_status_log(f"{process_type.capitalize()} process stopped by user")
            set_app_status(
                "idle",
                "Stopped by user",
                "",
                active=False,
                simple="🛑 Stopped",
            )
            return "🛑 Stopped", process_type
        except Exception as e:
            return f"⚠️ Error stopping process: {str(e)}", None
    return "⚠️ No running process to stop", None

def clear_all_data():
    """Clear all inputs, data, and outputs folders"""
    import shutil
    from pathlib import Path
    
    folders_to_clear = ["inputs", "data", "outputs"]
    cleared_folders = []
    errors = []
    
    for folder_name in folders_to_clear:
        folder_path = Path(folder_name)
        try:
            if folder_path.exists():
                shutil.rmtree(folder_path)
                folder_path.mkdir(exist_ok=True)  # Recreate empty folder
                cleared_folders.append(folder_name)
        except Exception as e:
            errors.append(f"{folder_name}: {str(e)}")
    
    if errors:
        return f"⚠️ Partially cleared. Errors: {', '.join(errors)}"
    elif cleared_folders:
        return f"🗑️ Successfully cleared: {', '.join(cleared_folders)}"
    else:
        return "✅ All folders already empty"

def top():
    from config import MAX_PARALLEL_FRS, UI_POLL_INTERVAL_SEC

    # Header row with title and clear button
    with gr.Row():
        with gr.Column(scale=8):
            gr.Markdown("## DECT | Don't Enjoy Creating Tests")
        with gr.Column(scale=2):
            clearButton = gr.Button("🗑️ Clear All", variant="stop", size="sm")
    
    with gr.Row():
        #########################
        # Left Column File Upload
        #########################
        with gr.Column():
            uploadFile = gr.File(label="Upload your file here", file_count="multiple", file_types=[".pdf"])
            savedPdfsList = gr.Textbox(
                label="Processed PDFs on disk",
                value=format_saved_processed_pdfs(),
                interactive=False,
                lines=4,
                max_lines=10,
            )

        #########################
        # Middle Column Buttons
        #########################
        with gr.Column():
            statusSimple = gr.Markdown(value=STATUS_READY_SIMPLE)
            with gr.Accordion("Detailed log", open=False):
                statusLog = gr.Textbox(
                    label="Activity log",
                    value=STATUS_READY_LOG,
                    interactive=False,
                    lines=12,
                    max_lines=24,
                )
            
            with gr.Row():
                _downloads_ready = results_download_available()
                _json_download = get_json_download_path() if _downloads_ready else None
                _csv_download = get_csv_download_path() if _downloads_ready else None
                downloadJsonButton = gr.DownloadButton(
                    "📥 Download JSON",
                    value=_json_download,
                    interactive=bool(_json_download),
                    size="md",
                )
                downloadCsvButton = gr.DownloadButton(
                    "📥 Download CSV",
                    value=_csv_download,
                    interactive=bool(_csv_download),
                    size="md",
                )

            with gr.Row():
                processPdfButton = gr.Button("1. Process PDF", interactive=False)
                runButton = gr.Button("2. Run", interactive=False)
                stopButton = gr.Button("🛑 Stop", interactive=False, variant="stop", size="sm")

            parallelFrSlider = gr.Slider(
                minimum=1,
                maximum=99,
                step=1,
                value=MAX_PARALLEL_FRS,
                label="Parallel FRs",
                info=(
                    "Max FRs running LLM steps at the same time. "
                    "Cloud API: raise if your quota allows; local/Ollama: try 2–4."
                ),
            )

        #########################
        # Right Column Result Snippet
        #########################
        with gr.Column():
            resultSnippet = gr.Dataframe(
                value=load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True),
                label="Result Snippet (First 5 test cases)",
                wrap=True,
                column_widths=RESULTS_COLUMN_WIDTHS,
                elem_classes=["dect-df"],
            )
    
    # Task Selector in its own row below the three columns
    with gr.Row():
        with gr.Column():
            task_selector = create_task_selector()
    
    # Event handlers with improved progress coverage and status updates
    
    # Function to handle pre-analysis setup (enable stop button)
    def start_analysis():
        """Prepare for analysis and enable stop button."""
        from core.status import set_app_status, get_status_ui

        set_app_status(
            "pipeline",
            "Preparing analysis",
            "Saving selected tasks...",
            active=True,
            simple="🚀 Preparing analysis…",
        )
        simple, detail = get_status_ui()
        return (
            gr.update(interactive=False),
            gr.update(interactive=True),
            simple,
            detail,
        )

    def complete_analysis(max_parallel):
        """Create tasks JSON, run pipeline subprocess, yield status while running."""
        from core.status import set_app_status, get_status_ui

        max_parallel = int(max_parallel)
        json_result, json_success = task_selector["create_tasks_json_file"]()
        snippet = load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True)

        if not json_success:
            yield (
                *download_buttons_update(False),
                json_result,
                STATUS_READY_LOG,
                snippet,
                gr.update(interactive=True),
                gr.update(interactive=False),
                gr.update(interactive=True),
            )
            return

        set_app_status(
            "pipeline",
            "Task list saved",
            json_result[:200],
            active=True,
            simple="🚀 Starting test pipeline…",
        )
        simple, detail = get_status_ui()
        yield (
            *download_buttons_update(False),
            simple,
            detail,
            snippet,
            gr.update(interactive=False),
            gr.update(interactive=True),
            gr.update(interactive=False),
        )

        try:
            process = _start_pipeline_subprocess(max_parallel)
        except Exception as e:
            set_app_status(
                "error",
                "Failed to start pipeline",
                str(e),
                active=False,
                simple="❌ Failed to start pipeline",
            )
            simple, detail = get_status_ui()
            yield (
                *download_buttons_update(False),
                simple,
                detail,
                snippet,
                gr.update(interactive=True),
                gr.update(interactive=False),
                gr.update(interactive=True),
            )
            return

        while process.poll() is None:
            time.sleep(1.0)
            simple, detail = get_status_ui()
            yield (
                *download_buttons_update(False),
                simple,
                detail,
                load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True),
                gr.update(interactive=False),
                gr.update(interactive=True),
                gr.update(interactive=False),
            )

        success, final_status = _finish_pipeline_subprocess(process)
        snippet = load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True)
        _, detail = get_status_ui()
        yield (
            *(download_buttons_state() if success else download_buttons_update(False)),
            final_status,
            detail,
            snippet,
            gr.update(interactive=True),
            gr.update(interactive=False),
            gr.update(interactive=True),
        )

    runButton.click(
        fn=start_analysis,
        inputs=None,
        outputs=[runButton, stopButton, statusSimple, statusLog],
    ).then(
        fn=complete_analysis,
        inputs=[parallelFrSlider],
        outputs=[
            downloadJsonButton,
            downloadCsvButton,
            statusSimple,
            statusLog,
            resultSnippet,
            runButton,
            stopButton,
            parallelFrSlider,
        ],
        show_progress="full",
        show_progress_on=[statusSimple, statusLog, processPdfButton, runButton],
    )

    def _task_selector_unchanged():
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )

    def process_pdf_and_refresh(pdf_files):
        """Process PDF with live status updates in the status textbox."""
        from core.status import (
            begin_pdf_processing,
            end_pdf_processing,
            get_status_ui,
            is_pdf_cancel_requested,
            set_app_status,
        )
        from utils.pdf2img import pdf_to_images_with_progress

        run_btn = gr.update(interactive=False)
        process_btn = gr.update(interactive=False)
        stop_btn = gr.update(interactive=False)
        unchanged = _task_selector_unchanged()

        saved_unchanged = gr.update()

        if not pdf_files:
            set_app_status(
                "error",
                "No files selected",
                "Upload a PDF first",
                active=False,
                simple="❌ No files selected",
            )
            simple, detail = get_status_ui()
            yield run_btn, simple, detail, saved_unchanged, process_btn, stop_btn, *unchanged
            return

        begin_pdf_processing()
        process_btn = gr.update(interactive=False)
        stop_btn = gr.update(interactive=True)
        try:
            success = False
            for simple, detail, done in pdf_to_images_with_progress(pdf_files):
                yield run_btn, simple, detail, saved_unchanged, process_btn, stop_btn, *unchanged
                if done:
                    success = not is_pdf_cancel_requested()
                    break

            stop_btn = gr.update(interactive=False)
            if is_pdf_cancel_requested():
                simple, detail = get_status_ui()
                process_btn = gr.update(interactive=True)
                yield run_btn, simple, detail, saved_unchanged, process_btn, stop_btn, *unchanged
                return

            if not success:
                set_app_status(
                    "error",
                    "PDF processing failed",
                    "Check terminal logs",
                    active=False,
                    simple="❌ PDF processing failed",
                )
                simple, detail = get_status_ui()
                process_btn = gr.update(interactive=True)
                yield run_btn, simple, detail, saved_unchanged, process_btn, stop_btn, *unchanged
                return
        finally:
            end_pdf_processing()

        task_selector["selector_instance"].load_json_files()
        has_files = task_selector["selector_instance"].has_files()
        file_options = task_selector["selector_instance"].get_file_options()
        initial_file = file_options[0] if file_options else None

        initial_requirements = []
        if initial_file:
            initial_requirements, _ = (
                task_selector["selector_instance"].get_requirements_for_file(initial_file)
            )

        if not has_files:
            output_message = (
                "📂 No processed PDFs found.\n\n"
                "Please upload and process a PDF first using the '1. Process PDF' button above."
            )
            title_text = "📋 Task selector ⚠️ (no PDFs processed yet)"
        else:
            output_message = "No tasks selected"
            title_text = "📋 Task selector"

        simple, detail = get_status_ui()
        yield (
            gr.update(interactive=False),
            simple,
            detail,
            format_saved_processed_pdfs(),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(choices=file_options, value=initial_file, interactive=has_files),
            gr.update(choices=initial_requirements, value=[], interactive=has_files),
            output_message,
            gr.update(interactive=has_files),
            gr.update(interactive=has_files),
            gr.update(value=title_text),
        )

    processPdfButton.click(
        fn=process_pdf_and_refresh,
        inputs=[uploadFile],
        outputs=[
            runButton,
            statusSimple,
            statusLog,
            savedPdfsList,
            processPdfButton,
            stopButton,
            task_selector["file_dropdown"],
            task_selector["requirements_selector"],
            task_selector["selected_tasks_output"],
            task_selector["select_all_btn"],
            task_selector["deselect_all_btn"],
            task_selector["title_markdown"],
        ],
        show_progress="full",
        show_progress_on=[statusSimple, statusLog, processPdfButton],
    )
    
    # Connect task selection to run button state
    task_selector['selection_status'].change(
        fn=checkTaskSelection,
        inputs=[task_selector['selection_status']],
        outputs=[runButton]
    )
    
    uploadFile.change(
        fn=on_files_uploaded,
        inputs=uploadFile,
        outputs=[processPdfButton, statusSimple, statusLog],
    )
    
    def poll_status_and_results():
        """Periodic refresh for status line, log, and result snippet."""
        simple, detail = get_status_outputs()
        return (
            simple,
            detail,
            load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True),
            format_saved_processed_pdfs(),
        )

    def poll_status_tasks_and_results(current_file):
        """Refresh status, results snippet, and task selector from disk."""
        simple, detail, snippet, saved_pdfs = poll_status_and_results()
        task_updates = task_selector["sync_task_files"](current_file)
        return (simple, detail, snippet, saved_pdfs, *task_updates)

    status_timer = gr.Timer(value=UI_POLL_INTERVAL_SEC)
    status_timer.tick(
        fn=poll_status_tasks_and_results,
        inputs=[task_selector["file_dropdown"]],
        outputs=[
            statusSimple,
            statusLog,
            resultSnippet,
            savedPdfsList,
            task_selector["file_dropdown"],
            task_selector["requirements_selector"],
            task_selector["selected_tasks_output"],
            task_selector["select_all_btn"],
            task_selector["deselect_all_btn"],
            task_selector["title_markdown"],
        ],
    )

    gr.Blocks.load(
        None,
        fn=download_buttons_state,
        inputs=None,
        outputs=[downloadJsonButton, downloadCsvButton],
    )

    # Clear button functionality - resets everything to initial state
    def clear_all_and_reset():
        """Clear all data and reset UI to initial state"""
        clear_status = clear_all_data()
        
        # Reset task selector
        task_selector['selector_instance'].load_json_files()
        has_files = task_selector['selector_instance'].has_files()
        file_options = task_selector['selector_instance'].get_file_options()
        
        if current_process.get("process"):
            stop_current_process()
        from core.status import clear_app_status, end_pdf_processing

        end_pdf_processing()
        clear_app_status()

        return [
            None,  # Clear uploadFile
            gr.update(interactive=False),  # Disable processPdfButton
            gr.update(interactive=False),  # Disable runButton
            gr.update(interactive=False),  # Disable stopButton
            *download_buttons_update(False),
            STATUS_READY_SIMPLE,
            STATUS_READY_LOG,
            pd.DataFrame(columns=[  # Reset resultSnippet to empty table
                'FR ID', 'Test Case', 'Precondition', 'Steps', 'Test Data', 
                'Expected Result', 'Environment', 'Actual Result', 
                'Test Status (Pass / Fail)', 'Jira Bug Link'
            ]),
            SAVED_PDFS_EMPTY,
            gr.update(choices=file_options, value=None, interactive=has_files),  # Reset file_dropdown
            gr.update(choices=[], value=[], interactive=has_files),  # Reset requirements_selector
            "No tasks selected" if has_files else "📂 No processed PDFs found.\n\nPlease upload and process a PDF first using the '1. Process PDF' button above.",  # Reset selected_tasks_output
            "📋 Task selector" if has_files else "📋 Task selector ⚠️ (no PDFs processed yet)",
        ]
    
    # Stop button functionality
    def handle_stop():
        """Handle stop button click (pipeline subprocess or in-thread PDF processing)."""
        stop_message, kind = stop_current_process()
        simple, detail = get_status_outputs()
        status_simple = (
            simple if "🛑" in stop_message or "⚠️" in stop_message else stop_message
        )

        if kind == "pdf":
            return (
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(interactive=True),
                status_simple,
                detail,
            )
        return (
            gr.update(interactive=True),
            gr.update(interactive=False),
            gr.update(),
            status_simple,
            detail,
        )

    stopButton.click(
        fn=handle_stop,
        inputs=None,
        outputs=[runButton, stopButton, processPdfButton, statusSimple, statusLog],
    )
    
    clearButton.click(
        fn=clear_all_and_reset,
        inputs=None,
        outputs=[
            uploadFile,
            processPdfButton,
            runButton,
            stopButton,
            downloadJsonButton,
            downloadCsvButton,
            statusSimple,
            statusLog,
            resultSnippet,
            savedPdfsList,
            task_selector['file_dropdown'],
            task_selector['requirements_selector'],
            task_selector['selected_tasks_output'],
            task_selector['title_markdown']
        ]
    )

    gr.Markdown("---")