import gradio as gr
import pandas as pd
from io import StringIO
from utils.mockData import dummyData

dummyTasks = ["Task 1", "Task 2", "Task 3"]
def top():
    gr.Markdown("# DECT | Don't Enjoy Creating Tests")
    with gr.Row():
        with gr.Column():
            uploadFile = gr.File(label="Upload your file here", file_types=[".pdf"])
        with gr.Column():
            downloadButton = gr.Button("Download Results", interactive=False)
            runButton = gr.Button("Run", interactive=False)
            selectTasks = gr.Dropdown(choices=dummyTasks, value=dummyTasks, label="Select Task", multiselect=True, interactive=True)
        with gr.Column():
            resultSnippet = gr.Dataframe(value=dummyData, label="Result Snippet")
    gr.Markdown("---")