from rich import print
import gradio as gr
from components.top import top
from components.mid import mid
from components.bot import bot
from components.ui_styles import GRADIO_DF_CSS
from fastapi import FastAPI

APP_CSS = """
.gradio-container .markdown h1 { font-size: 1.35rem !important; font-weight: 600 !important; margin: 0.35rem 0 !important; }
.gradio-container .markdown h2 { font-size: 1.15rem !important; font-weight: 600 !important; margin: 0.3rem 0 !important; }
.gradio-container .markdown h3 { font-size: 1.05rem !important; font-weight: 600 !important; margin: 0.25rem 0 !important; }
.gradio-container .markdown p { margin: 0.2rem 0 !important; }
""" + GRADIO_DF_CSS

with gr.Blocks() as demo:
    top()
    mid()
    bot()

fastapi_app = FastAPI()
app = gr.mount_gradio_app(
    app=fastapi_app,
    blocks=demo,
    path="/",
    allowed_paths=["outputs"],
    css=APP_CSS,
)

# if __name__ == "__main__":
#     demo.launch(quiet=False)

if __name__ == "__main__":
    import uvicorn
    print("Running FastAPI + Gradio app...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=7860)