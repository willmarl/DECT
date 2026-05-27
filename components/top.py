import gradio as gr
import pandas as pd
from io import StringIO
from components.taskSelector import create_task_selector
from time import sleep
import json
from pathlib import Path
import threading
import time
import subprocess
import signal
import os

# Global variable to track running processes
current_process = {}

def truncate_text(text, max_length=30):
    """Truncate text to max_length characters with ellipsis, preserving word boundaries when possible"""
    if not text or len(text) <= max_length:
        return text
    
    # Try to truncate at word boundary
    truncated = text[:max_length].rstrip()
    
    # If we can find a space within the last 10 characters, truncate there
    last_space = truncated.rfind(' ', max(0, max_length - 10))
    if last_space > max_length // 2:  # Only if the space is not too early
        truncated = text[:last_space].rstrip()
    
    return truncated + "..."

def truncate_dataframe_cells(df, max_length=30, exclude_columns=None, custom_lengths=None):
    """Truncate text in all DataFrame cells with customizable lengths per column"""
    if exclude_columns is None:
        exclude_columns = ['FR ID', 'Environment', 'Test Status (Pass / Fail)']
    
    if custom_lengths is None:
        custom_lengths = {
            'Test Case': 40,  # Slightly longer for test case titles
            'Steps': 35,      # A bit longer for steps
            'Test Data': 25,  # Shorter for test data
            'Precondition': 35,
            'Expected Result': 40,
            'Actual Result': 30,
            'Jira Bug Link': 20
        }
    
    df_truncated = df.copy()
    for column in df_truncated.columns:
        if column not in exclude_columns:
            # Use custom length if specified, otherwise use default
            col_max_length = custom_lengths.get(column, max_length)
            df_truncated[column] = df_truncated[column].astype(str).apply(
                lambda x: truncate_text(x, col_max_length)
            )
    return df_truncated

def load_final_output_as_dataframe(limit_rows=None, truncate_for_snippet=False):
    """Load final_output.json and convert to pandas DataFrame for display"""
    final_output_path = Path("outputs/final_output.json")
    
    if not final_output_path.exists():
        # Return empty DataFrame with proper column structure
        return pd.DataFrame(columns=[
            'FR ID', 'Test Case', 'Precondition', 'Steps', 'Test Data', 
            'Expected Result', 'Environment', 'Actual Result', 
            'Test Status (Pass / Fail)', 'Jira Bug Link'
        ])
    
    try:
        with open(final_output_path, 'r') as f:
            data = json.load(f)
        
        # Extract test cases from all FRs
        rows = []
        for test_suite in data.get('test_suite', []):
            fr_id = test_suite.get('fr_id', 'Unknown')
            for test_case in test_suite.get('test_cases', []):
                rows.append({
                    'FR ID': fr_id,
                    'Test Case': test_case.get('title', ''),
                    'Precondition': test_case.get('precondition', ''),
                    'Steps': test_case.get('steps', ''),
                    'Test Data': test_case.get('test_data', ''),
                    'Expected Result': test_case.get('expected_result', ''),
                    'Environment': test_case.get('environment', ''),
                    'Actual Result': test_case.get('actual_result', ''),
                    'Test Status (Pass / Fail)': test_case.get('status', ''),
                    'Jira Bug Link': test_case.get('jira_bug_link', '')
                })
        
        if rows:
            df = pd.DataFrame(rows)
            # Limit rows if specified (for snippet view)
            if limit_rows:
                df = df.head(limit_rows)
            
            # Truncate text for snippet view to improve readability
            if truncate_for_snippet:
                df = truncate_dataframe_cells(df, max_length=30)
            
            return df
        else:
            # Return empty DataFrame if no test cases found
            return pd.DataFrame(columns=[
                'FR ID', 'Test Case', 'Precondition', 'Steps', 'Test Data', 
                'Expected Result', 'Environment', 'Actual Result', 
                'Test Status (Pass / Fail)', 'Jira Bug Link'
            ])
            
    except Exception as e:
        print(f"Error loading final output: {e}")
        # Return empty DataFrame on error instead of dummy data
        return pd.DataFrame(columns=[
            'FR ID', 'Test Case', 'Precondition', 'Steps', 'Test Data', 
            'Expected Result', 'Environment', 'Actual Result', 
            'Test Status (Pass / Fail)', 'Jira Bug Link'
        ])

def get_status_outputs():
    """Return (simple_markdown, detail_log) for the status UI."""
    from core.status import get_status_ui
    return get_status_ui()


STATUS_READY_SIMPLE = "✅ Ready — upload a PDF to begin"
STATUS_READY_LOG = "No activity yet."

def isButtonValid(x):
    if x is not None and len(x) > 0:
        return gr.update(interactive=True)
    else:
        return gr.update(interactive=False)


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

def generate_csv_from_json():
    """Generate CSV file from final_output.json"""
    from pathlib import Path
    import pandas as pd
    
    outputs_dir = Path("outputs")
    json_path = outputs_dir / "final_output.json"
    csv_path = outputs_dir / "final_output.csv"
    
    if not json_path.exists():
        return False, "JSON file not found"
    
    try:
        # Use the existing function to convert JSON to DataFrame
        df = load_final_output_as_dataframe(limit_rows=None, truncate_for_snippet=False)
        
        if not df.empty:
            # Save as CSV with proper formatting
            df.to_csv(csv_path, index=False, encoding='utf-8')
            return True, f"CSV generated successfully: {csv_path}"
        else:
            return False, "No data to export to CSV"
            
    except Exception as e:
        return False, f"Error generating CSV: {str(e)}"

def prepare_download():
    """Prepare the final output files (JSON and CSV) for download"""
    from pathlib import Path
    import zipfile
    
    # Ensure outputs directory exists
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    
    json_path = outputs_dir / "final_output.json"
    csv_path = outputs_dir / "final_output.csv"
    zip_path = outputs_dir / "test_results.zip"
    
    if json_path.exists():
        # Generate CSV version
        csv_success, csv_message = generate_csv_from_json()
        
        # Create a zip file with both JSON and CSV
        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Add JSON file
                zipf.write(json_path, json_path.name)
                
                # Add CSV file if it was generated successfully
                if csv_success and csv_path.exists():
                    zipf.write(csv_path, csv_path.name)
            
            return gr.update(value=str(zip_path), visible=True)
            
        except Exception as e:
            # Fallback to JSON only if zip creation fails
            return gr.update(value=str(json_path), visible=True)
    else:
        # If file doesn't exist, create a temporary error file
        error_file = outputs_dir / "error.txt"
        error_file.write_text("Error: final_output.json not found. Please run the analysis first.")
        return gr.update(value=str(error_file), visible=True)

def stop_current_process():
    """Stop the currently running process"""
    if current_process.get("process") and current_process.get("type"):
        try:
            process = current_process["process"]
            process_type = current_process["type"]
            
            # Terminate the process
            if os.name == 'nt':  # Windows
                process.terminate()
            else:  # Unix/Linux/macOS
                process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
            
            # Clear the process tracking
            current_process.clear()
            
            from core.status import set_app_status, append_status_log

            append_status_log(f"{process_type.capitalize()} process stopped by user")
            set_app_status(
                "idle",
                "Stopped by user",
                "",
                active=False,
                simple="🛑 Stopped",
            )
            return "🛑 Stopped"
        except Exception as e:
            return f"⚠️ Error stopping process: {str(e)}"
    else:
        return "⚠️ No running process to stop"

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
            gr.Markdown("# DECT | Don't Enjoy Creating Tests")
        with gr.Column(scale=2):
            clearButton = gr.Button("🗑️ Clear All", variant="stop", size="sm")
    
    with gr.Row():
        #########################
        # Left Column File Upload
        #########################
        with gr.Column():
            uploadFile = gr.File(label="Upload your file here", file_count="multiple", file_types=[".pdf"])
        
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
            
            downloadButton = gr.Button("📥 Download Results (JSON + CSV)", interactive=False)
            downloadFile = gr.File(visible=False)

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
                wrap=True
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
                gr.update(interactive=False),
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
            gr.update(interactive=False),
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
                gr.update(interactive=False),
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
                gr.update(interactive=False),
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
            gr.update(interactive=success),
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
            downloadButton,
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
        from core.status import get_status_ui, set_app_status
        from utils.pdf2img import pdf_to_images_with_progress

        run_btn = gr.update(interactive=False)
        unchanged = _task_selector_unchanged()

        if not pdf_files:
            set_app_status(
                "error",
                "No files selected",
                "Upload a PDF first",
                active=False,
                simple="❌ No files selected",
            )
            simple, detail = get_status_ui()
            yield run_btn, simple, detail, *unchanged
            return

        success = False
        for simple, detail, done in pdf_to_images_with_progress(pdf_files):
            yield run_btn, simple, detail, *unchanged
            success = done

        if not success:
            set_app_status(
                "error",
                "PDF processing failed",
                "Check terminal logs",
                active=False,
                simple="❌ PDF processing failed",
            )
            simple, detail = get_status_ui()
            yield run_btn, simple, detail, *unchanged
            return

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
            title_text = "### 📋 Task Selector ⚠️ (Disabled - No PDFs Processed)"
        else:
            output_message = "No tasks selected"
            title_text = "### 📋 Task Selector"

        simple, detail = get_status_ui()
        yield (
            gr.update(interactive=False),
            simple,
            detail,
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
    
    # Connect download button to prepare download file
    downloadButton.click(
        fn=prepare_download,
        inputs=None,
        outputs=[downloadFile]
    )
    
    def poll_status_and_results():
        """Periodic refresh for status line, log, and result snippet."""
        simple, detail = get_status_outputs()
        return (
            simple,
            detail,
            load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True),
        )

    def poll_status_tasks_and_results(current_file):
        """Refresh status, results snippet, and task selector from disk."""
        simple, detail, snippet = poll_status_and_results()
        task_updates = task_selector["sync_task_files"](current_file)
        return (simple, detail, snippet, *task_updates)

    status_timer = gr.Timer(value=UI_POLL_INTERVAL_SEC)
    status_timer.tick(
        fn=poll_status_tasks_and_results,
        inputs=[task_selector["file_dropdown"]],
        outputs=[
            statusSimple,
            statusLog,
            resultSnippet,
            task_selector["file_dropdown"],
            task_selector["requirements_selector"],
            task_selector["selected_tasks_output"],
            task_selector["select_all_btn"],
            task_selector["deselect_all_btn"],
            task_selector["title_markdown"],
        ],
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

        from core.status import clear_app_status
        clear_app_status()

        return [
            None,  # Clear uploadFile
            gr.update(interactive=False),  # Disable processPdfButton
            gr.update(interactive=False),  # Disable runButton
            gr.update(interactive=False),  # Disable downloadButton
            STATUS_READY_SIMPLE,
            STATUS_READY_LOG,
            pd.DataFrame(columns=[  # Reset resultSnippet to empty table
                'FR ID', 'Test Case', 'Precondition', 'Steps', 'Test Data', 
                'Expected Result', 'Environment', 'Actual Result', 
                'Test Status (Pass / Fail)', 'Jira Bug Link'
            ]),
            gr.update(choices=file_options, value=None, interactive=has_files),  # Reset file_dropdown
            gr.update(choices=[], value=[], interactive=has_files),  # Reset requirements_selector
            "No tasks selected" if has_files else "📂 No processed PDFs found.\n\nPlease upload and process a PDF first using the '1. Process PDF' button above.",  # Reset selected_tasks_output
            "### 📋 Task Selector" if has_files else "### 📋 Task Selector ⚠️ (Disabled - No PDFs Processed)",  # Reset title_markdown
        ]
    
    # Stop button functionality
    def handle_stop():
        """Handle stop button click"""
        stop_message = stop_current_process()
        
        # Re-enable run button, disable stop button
        simple, detail = get_status_outputs()
        return (
            gr.update(interactive=True),
            gr.update(interactive=False),
            simple if "🛑" in stop_message or "⚠️" in stop_message else stop_message,
            detail,
        )

    stopButton.click(
        fn=handle_stop,
        inputs=None,
        outputs=[runButton, stopButton, statusSimple, statusLog],
    )
    
    clearButton.click(
        fn=clear_all_and_reset,
        inputs=None,
        outputs=[
            uploadFile,
            processPdfButton, 
            runButton,
            downloadButton,
            statusSimple,
            statusLog,
            resultSnippet,
            task_selector['file_dropdown'],
            task_selector['requirements_selector'],
            task_selector['selected_tasks_output'],
            task_selector['title_markdown']
        ]
    )

    gr.Markdown("---")