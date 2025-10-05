from rich import print
import gradio as gr
from components.top import top
from components.mid import mid
from components.bot import bot
from fastapi import FastAPI

with gr.Blocks() as demo:
    top()
    mid()
    bot()

fastapi_app = FastAPI()
app = gr.mount_gradio_app(app=fastapi_app, blocks=demo, path="/")

# if __name__ == "__main__":
#     demo.launch(quiet=False)

if __name__ == "__main__":
    import uvicorn
    print("Running FastAPI + Gradio app...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=7860)