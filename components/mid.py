import gradio as gr

css = "text-align: center; margin-top: 20px;"
def tab1():
    gr.Dataframe(["filler text for tab 1"])
def tab2():
    gr.Dataframe(["filler text for tab 2"])
def tab3():
    gr.Dataframe(["filler text for tab 3"])
def tab4():
    gr.Dataframe(["filler text for tab 4"])
def tab5():
    gr.Dataframe(["filler text for tab 5"])
def tab6():
    gr.Dataframe(["filler text for tab 6"])
def tab7():
    gr.Dataframe(["filler text for tab 7"])
def tab8():
    gr.Dataframe(["filler text for tab 8"])

def mid():
    with gr.Row():
        selectFr = gr.Dropdown(choices=["FR-1", "FR-2", "FR-3"], label="Select FR", multiselect=False, interactive=True)
        gr.Markdown(
            f"""
            <h2 style="{css}">
                Task 2 out of 3
            </h2>
            """
        )
        gr.Markdown("") # for spacing
    with gr.Tabs():
        with gr.Tab("Step 1: Atomic blocks"):
            tab1()
        with gr.Tab("Step 2: Paritions"):
            tab2()
        with gr.Tab("Step 3: Boundaries"):
            tab3()
        with gr.Tab("Step 4: Values"):
            tab4()
        with gr.Tab("Step 5: Unified list"):
            tab5()
        with gr.Tab("Step 6: Deduped list"):
            tab6()
        with gr.Tab("Step 7: Organized data"):
            tab7()
        with gr.Tab("Step 8: Test cases"):
            tab8()
    gr.Markdown("---")