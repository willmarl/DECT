import gradio as gr
import pandas as pd
from io import StringIO
from utils.mockData import dummyData
from preprocessor.pdf2img import pdf_to_images
from components.taskSelector import create_task_selector
from time import sleep

def isButtonValid(x):
    if x is not None and len(x) > 0:
        return gr.update(interactive=True)
    else:
        return gr.update(interactive=False)

# Note: updateRunButton and processPdfAndUpdateButton functions have been replaced 
# with the inline process_pdf_and_refresh function in the top() function

def long_running_task():
    sleep(1.5) # Simulate a long process
    return True

def updateDownloadButton():
    x = long_running_task()
    status = "✅ Analysis complete! Results ready for download." if x else "❌ Analysis failed"
    return gr.update(interactive=x), status

def checkTaskSelection(selection_status):
    """Check if tasks are selected to enable/disable run button"""
    is_selected = selection_status == "True"
    return gr.update(interactive=is_selected)

def top():
    gr.Markdown("# DECT | Don't Enjoy Creating Tests")
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
                lines=1
            )
            
            downloadButton = gr.Button("Download Results", interactive=False)

            with gr.Row():
                processPdfButton = gr.Button("1. Process PDF", interactive=False)
                runButton = gr.Button("2. Run", interactive=False)

        #########################
        # Right Column Result Snippet
        #########################
        with gr.Column():
            resultSnippet = gr.Dataframe(value=dummyData, label="Result Snippet")
    
    # Task Selector in its own row below the three columns
    with gr.Row():
        with gr.Column():
            task_selector = create_task_selector()
    
    # Event handlers with improved progress coverage and status updates
    runButton.click(
        fn=updateDownloadButton, 
        inputs=None, 
        outputs=[downloadButton, statusText], 
        show_progress="full",
        show_progress_on=[downloadButton, processPdfButton, runButton, statusText]
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
        show_progress_on=[downloadButton, processPdfButton, runButton, statusText]
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

    gr.Markdown("---")