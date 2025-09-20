from rich import print
from schema import QAschema
import graph as g1
import gradio as gr

def sendToAgent(*inputs):
    invokePrep = {"debug": inputs[0]}
    finalState = g1.graph.invoke(QAschema(**invokePrep))
    print(finalState) #for debugging
    return finalState["debug"]

inputs = [
    gr.Textbox(lines=2, placeholder="Enter your question here..."),
    gr.File(label="Upload a file")
]

output = gr.Textbox(label="Agent Response", lines=10)

interface = gr.Interface(
    fn=sendToAgent,
    inputs=inputs,
    outputs=output,
)

if __name__ == "__main__":
    interface.launch()
