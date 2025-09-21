import gradio as gr
from utils.mockData import dummyData

def bot():
    gr.Markdown("## Final compiled test cases")
    gr.Dataframe(dummyData)