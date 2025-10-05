import gradio as gr
import pandas as pd
from io import StringIO
from utils.pdf2img import pdf_to_images
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

def monitor_pipeline_status():
    """Monitor pipeline progress by checking step files"""
    status_file = Path("pipeline_status.txt")
    
    while True:
        try:
            if status_file.exists():
                with open(status_file, 'r') as f:
                    status = f.read().strip()
                    return status
        except:
            pass
        
        # Check for step files as fallback
        logbook_base = Path("data/pdf_logbook")
        if logbook_base.exists():
            latest_step = 0
            total_frs = 0
            completed_frs = 0
            
            for pdf_dir in logbook_base.iterdir():
                if pdf_dir.is_dir():
                    for fr_dir in pdf_dir.iterdir():
                        if fr_dir.is_dir() and fr_dir.name.startswith('FR-'):
                            total_frs += 1
                            fr_latest_step = 0
                            
                            for step in range(1, 9):
                                step_file = fr_dir / f"step{step}.json"
                                if step_file.exists():
                                    fr_latest_step = step
                            
                            if fr_latest_step == 8:
                                completed_frs += 1
                            
                            latest_step = max(latest_step, fr_latest_step)
            
            if total_frs > 0:
                if completed_frs == total_frs:
                    return f"✅ Pipeline completed! All {total_frs} FRs processed through all 8 steps."
                else:
                    return f"🔄 Processing step {latest_step}/8 | Completed FRs: {completed_frs}/{total_frs}"
        
        return "Ready to process PDFs"

def get_current_pipeline_status():
    """Get the current pipeline status for display"""
    return monitor_pipeline_status()

def isButtonValid(x):
    if x is not None and len(x) > 0:
        return gr.update(interactive=True)
    else:
        return gr.update(interactive=False)

# Note: updateRunButton and processPdfAndUpdateButton functions have been replaced 
# with the inline process_pdf_and_refresh function in the top() function

def run_pipeline_analysis():
    """Run the actual pipeline analysis using simple_run.py"""
    import sys
    from pathlib import Path
    
    # Write initial status
    status_file = Path("pipeline_status.txt")
    status_file.write_text("🚀 Starting pipeline analysis...")
    
    try:
        # Start the pipeline process
        process = subprocess.Popen([
            sys.executable, "-m", "core.simple_run"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=Path.cwd())
        
        # Track the process globally
        current_process["process"] = process
        current_process["type"] = "pipeline"
        
        # Wait for completion
        stdout, stderr = process.communicate()
        
        # Clear the process tracking
        current_process["process"] = None
        current_process["type"] = None
        
        if process.returncode == 0:
            status_file.write_text("✅ Pipeline completed successfully!")
            return True, f"✅ Pipeline completed successfully!\n\nOutput:\n{stdout}"
        elif process.returncode == -signal.SIGTERM or process.returncode == -signal.SIGKILL:
            status_file.write_text("🛑 Pipeline stopped by user")
            return False, "🛑 Pipeline analysis was stopped by user"
        else:
            status_file.write_text("❌ Pipeline failed with error")
            return False, f"❌ Pipeline failed with error:\n{stderr}"
    except Exception as e:
        # Clear the process tracking on error
        current_process["process"] = None
        current_process["type"] = None
        status_file.write_text(f"❌ Error running pipeline: {str(e)}")
        return False, f"❌ Error running pipeline: {str(e)}"

def updateDownloadButton(create_tasks_json_func):
    """Create tasks JSON and then run the actual analysis pipeline"""
    # First create the tasks JSON file
    json_result, json_success = create_tasks_json_func()
    
    if not json_success:
        return gr.update(interactive=False), json_result
    
    # Run the actual pipeline analysis
    pipeline_success, pipeline_status = run_pipeline_analysis()
    
    if pipeline_success:
        status = f"{json_result}\n\n{pipeline_status}\n\n📥 Results ready for download!"
    else:
        status = f"{json_result}\n\n{pipeline_status}"
    
    return gr.update(interactive=pipeline_success), status

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
            
            # Update status
            status_file = Path("pipeline_status.txt")
            status_file.write_text(f"🛑 {process_type.capitalize()} process stopped by user")
            
            return f"🛑 {process_type.capitalize()} process stopped successfully"
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
            # Status display for user feedback
            statusText = gr.Textbox(
                label="Status", 
                value="Ready to process PDFs", 
                interactive=False,
                lines=2
            )
            
            downloadButton = gr.Button("📥 Download Results (JSON + CSV)", interactive=False)
            downloadFile = gr.File(visible=False)

            with gr.Row():
                processPdfButton = gr.Button("1. Process PDF", interactive=False)
                runButton = gr.Button("2. Run", interactive=False)
                stopButton = gr.Button("🛑 Stop", interactive=False, variant="stop", size="sm")
            
            # Add refresh button for real-time updates
            refreshButton = gr.Button("🔄 Refresh Status & Results", variant="secondary")

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
        """Prepare for analysis and enable stop button"""
        # Enable stop button, disable run button temporarily
        return (
            gr.update(interactive=False),  # Disable runButton
            gr.update(interactive=True),   # Enable stopButton
            "🚀 Starting pipeline analysis..."  # Update status
        )
    
    # Function to handle analysis completion
    def complete_analysis():
        """Run the actual analysis"""
        # Update status to show pipeline is starting
        status_update = "🚀 Starting pipeline analysis..."
        
        # Create tasks and run pipeline
        download_state, final_status = updateDownloadButton(task_selector['create_tasks_json_file'])
        
        # Load updated results
        updated_snippet = load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True)
        
        # Re-enable run button, disable stop button
        run_button_state = gr.update(interactive=True)
        stop_button_state = gr.update(interactive=False)
        
        return download_state, final_status, updated_snippet, run_button_state, stop_button_state
    
    runButton.click(
        fn=start_analysis,
        inputs=None,
        outputs=[runButton, stopButton, statusText]
    ).then(
        fn=complete_analysis,
        inputs=None,
        outputs=[downloadButton, statusText, resultSnippet, runButton, stopButton],
        show_progress="full",
        show_progress_on=[downloadButton, processPdfButton, resultSnippet]
    )
    
    # Connect PDF processing to enable/disable Run button based on success
    def process_pdf_and_refresh(pdf_files):
        """Process PDF and automatically refresh task selector"""
        success = pdf_to_images(pdf_files)
        status = "✅ PDF processed successfully! Select tasks below and then run analysis." if success else "❌ PDF processing failed"
        
        if success:
            # Refresh task selector files
            task_selector['selector_instance'].load_json_files()
            has_files = task_selector['selector_instance'].has_files()
            file_options = task_selector['selector_instance'].get_file_options()
            initial_file = file_options[0] if file_options else None
            
            # Get initial requirements
            initial_requirements = []
            if initial_file:
                initial_requirements, _ = task_selector['selector_instance'].get_requirements_for_file(initial_file)
            
            # Determine output message and title
            if not has_files:
                output_message = "📂 No processed PDFs found.\n\nPlease upload and process a PDF first using the '1. Process PDF' button above."
                title_text = "### 📋 Task Selector ⚠️ (Disabled - No PDFs Processed)"
            else:
                output_message = "No tasks selected"
                title_text = "### 📋 Task Selector"
            
            return [
                gr.update(interactive=False),  # Keep run button disabled until tasks selected
                status,
                gr.update(choices=file_options, value=initial_file, interactive=has_files),  # Update file dropdown
                gr.update(choices=initial_requirements, value=[], interactive=has_files),   # Update requirements
                output_message,  # Update output textbox
                gr.update(interactive=has_files),  # Refresh button
                gr.update(interactive=has_files),  # Select all button
                gr.update(interactive=has_files),  # Deselect all button
                gr.update(value=title_text),  # Update title
            ]
        else:
            return [
                gr.update(interactive=False),
                status,
                gr.update(),  # No change to dropdown
                gr.update(),  # No change to requirements
                gr.update(),  # No change to output
                gr.update(),  # No change to refresh button
                gr.update(),  # No change to select all button
                gr.update(),  # No change to deselect all button
                gr.update(),  # No change to title
            ]
    
    processPdfButton.click(
        fn=process_pdf_and_refresh, 
        inputs=[uploadFile], 
        outputs=[runButton, statusText, task_selector['file_dropdown'], task_selector['requirements_selector'], task_selector['selected_tasks_output'], task_selector['refresh_btn'], task_selector['select_all_btn'], task_selector['deselect_all_btn'], task_selector['title_markdown']], 
        show_progress="full", 
        show_progress_on=[downloadButton, processPdfButton, runButton]
    )
    
    # Connect task selection to run button state
    task_selector['selection_status'].change(
        fn=checkTaskSelection,
        inputs=[task_selector['selection_status']],
        outputs=[runButton]
    )
    
    # Connect the file upload change event to update the button state
    uploadFile.change(
        fn=isButtonValid, 
        inputs=uploadFile, 
        outputs=processPdfButton
    )
    
    # Connect download button to prepare download file
    downloadButton.click(
        fn=prepare_download,
        inputs=None,
        outputs=[downloadFile]
    )
    
    # Add periodic status and result updates (every 3 seconds when pipeline is running)
    def refresh_status_and_results():
        """Refresh status and results periodically"""
        current_status = get_current_pipeline_status()
        updated_results = load_final_output_as_dataframe(limit_rows=5, truncate_for_snippet=True)
        return current_status, updated_results
    
    # Connect refresh button functionality
    refreshButton.click(
        fn=refresh_status_and_results,
        inputs=None,
        outputs=[statusText, resultSnippet]
    )
    
    # Clear button functionality - resets everything to initial state
    def clear_all_and_reset():
        """Clear all data and reset UI to initial state"""
        clear_status = clear_all_data()
        
        # Reset task selector
        task_selector['selector_instance'].load_json_files()
        has_files = task_selector['selector_instance'].has_files()
        file_options = task_selector['selector_instance'].get_file_options()
        
        # Stop any running processes
        if current_process.get("process"):
            stop_current_process()
        
        # Reset to initial state
        return [
            None,  # Clear uploadFile
            gr.update(interactive=False),  # Disable processPdfButton
            gr.update(interactive=False),  # Disable runButton
            gr.update(interactive=False),  # Disable downloadButton
            f"{clear_status}\n\nReady to process PDFs",  # Reset statusText
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
        return (
            gr.update(interactive=True),   # Enable runButton
            gr.update(interactive=False),  # Disable stopButton
            stop_message  # Update statusText
        )
    
    stopButton.click(
        fn=handle_stop,
        inputs=None,
        outputs=[runButton, stopButton, statusText]
    )
    
    clearButton.click(
        fn=clear_all_and_reset,
        inputs=None,
        outputs=[
            uploadFile,
            processPdfButton, 
            runButton,
            downloadButton,
            statusText, 
            resultSnippet,
            task_selector['file_dropdown'],
            task_selector['requirements_selector'],
            task_selector['selected_tasks_output'],
            task_selector['title_markdown']
        ]
    )

    gr.Markdown("---")