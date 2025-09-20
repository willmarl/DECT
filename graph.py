from langgraph.graph import StateGraph, START, END
from schema import QAschema
from nodes import userInput, aiResponse

builder = StateGraph(QAschema)
builder.add_node("userInput", userInput)
builder.add_node("aiResponse", aiResponse)

builder.add_edge(START, "aiResponse")
builder.add_edge("aiResponse", END)

graph = builder.compile()

with open("graph.png", "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())