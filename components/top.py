import gradio as gr
import pandas as pd
from io import StringIO
from utils.mockData import dummyData
from preprocessor.pdf2img import pdf_to_images
from time import sleep

def isButtonValid(x):
    if x is not None and len(x) > 0:
        return gr.update(interactive=True)
    else:
        return gr.update(interactive=False)

def updateRunButton(success):
    """Convert boolean output from pdf_to_images to button state"""
    # update select task to pull from extractFR
    status = "✅ PDF processed successfully! Ready to run analysis." if success else "❌ PDF processing failed"
    return gr.update(interactive=success), status

def processPdfAndUpdateButton(pdf_files):
    """Process PDF and return button state update"""
    success = pdf_to_images(pdf_files)
    return updateRunButton(success)

def long_running_task():
    sleep(5) # Simulate a long process
    return True

def updateDownloadButton():
    x = long_running_task()
    status = "✅ Analysis complete! Results ready for download." if x else "❌ Analysis failed"
    return gr.update(interactive=x), status

dummyTasks = ["Task 1", "Task 2", "Task 3"]
def top():
    gr.Markdown("# DECT | Don't Enjoy Creating Tests")
    with gr.Row():
        #########################
        # Left Column File Upload
        #########################
        with gr.Column():
            uploadFile = gr.File(label="Upload your file here", file_count="multiple", file_types=[".pdf"])
        
        #########################
        # Middle Column Buttons and Dropdown
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
                
            selectTasks = gr.Dropdown(choices=dummyTasks, value=dummyTasks, label="Select Task", multiselect=True, interactive=True)
            
            # Event handlers with improved progress coverage and status updates
            runButton.click(
                fn=updateDownloadButton, 
                inputs=None, 
                outputs=[downloadButton, statusText], 
                show_progress="full",
                show_progress_on=[downloadButton, processPdfButton, runButton, statusText]
            )
            
            # Connect PDF processing to enable/disable Run button based on success
            processPdfButton.click(
                fn=processPdfAndUpdateButton, 
                inputs=uploadFile, 
                outputs=[runButton, statusText], 
                show_progress="full", 
                show_progress_on=[downloadButton, processPdfButton, runButton, statusText]
            )
            
            # Connect the file upload change event to update the button state
            uploadFile.change(
                fn=isButtonValid, 
                inputs=uploadFile, 
                outputs=processPdfButton
            )

        #########################
        # Right Column Result Snippet
        #########################
        with gr.Column():
            resultSnippet = gr.Dataframe(value=dummyData, label="Result Snippet")

    gr.Markdown("---")