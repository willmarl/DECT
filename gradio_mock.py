"""
gradio_vision.py
----------------
This is a prototype UI for DECT (Don't Enjoy Creating Tests).

⚠️ NOTE: This file is a *vision mockup* — it uses dummy data and
fixed outputs to demonstrate the intended user experience:
    - Upload a requirements PDF
    - Assign FRs (e.g., FR-1, FR-2, FR-3)
    - Watch live step-by-step progress
    - View per-step results in tabs
    - View a compiled test case table at the end
    - Download the final CSV

It is **not connected** to the LangGraph pipeline yet.
The real pipeline will replace the dummy data with actual outputs
(step1 → step8) generated from the requirements.

Use this file to:
    - Preview the vision of the final UI
    - Share design ideas
    - Guide future development
"""
import gradio as gr
import pandas as pd
import time

# Dummy step outputs (rectangular)
dummy_steps = {
    "FR-1": {
        "step1": pd.DataFrame({"Atomic Blocks": ["Dummy requirement A", "Dummy requirement B"]}),
        "step2": pd.DataFrame({
            "Class": ["Valid", "Invalid"],
            "Value": ["Dummy valid", "Dummy invalid"]
        }),
        "step3": pd.DataFrame({
            "Partition": ["Boundary", "Valid"],
            "Value": ["Example", "Example"]
        }),
    },
    "FR-2": {
        "step1": pd.DataFrame({"Atomic Blocks": ["Dummy requirement A", "Dummy requirement B"]}),
        "step2": pd.DataFrame({
            "Class": ["Valid", "Invalid"],
            "Value": ["Dummy valid", "Dummy invalid"]
        }),
        "step3": pd.DataFrame({
            "Partition": ["Boundary", "Valid"],
            "Value": ["Example", "Example"]
        }),
    }
}

# Dummy final compiled output
final_cases = pd.DataFrame([
    {
        "FR ID": "FR-1",
        "Test Case": "Verify the user can enter only Latin characters (2-25 characters)",
        "Precondition": "The user is on the homepage. The first name field is empty.",
        "Steps": "Enter only Latin characters (2-25 characters)",
        "Test Data": "**Lula**",
        "Expected Result": "Latin characters are accepted.",
        "Environment": "Test Environment",
        "Actual Result": "Latin characters are accepted.",
        "Test Status (Pass / Fail)": "",
        "Jira Bug Link": ""
    },
    {
        "FR ID": "FR-1",
        "Test Case": "Verify the user cannot enter numbers",
        "Precondition": "The user is on the homepage. The first name field is empty.",
        "Steps": "Enter numbers",
        "Test Data": "**123**",
        "Expected Result": "Numbers are not not accepted.",
        "Environment": "Test Environment",
        "Actual Result": "Numbers are not accepted.",
        "Test Status (Pass / Fail)": "",
        "Jira Bug Link": ""
    }
])

# Simulate processing
def process_pdfs(pdf, assigned_frs):
    assigned = [fr.strip() for fr in assigned_frs.split(",")]
    for idx, fr in enumerate(assigned, 1):
        for step_num in range(1, 4):  # simulate 3 steps
            yield f"Task ({fr}) {step_num}/3", None, None
            time.sleep(0.5)
    yield "All tasks completed.", final_cases, "final_output.csv"

with gr.Blocks() as demo:
    gr.Markdown("# DECT — Don’t Enjoy Creating Tests?")
    gr.Markdown("Upload requirements PDF, assign FRs, and watch live QA pipeline progress.")

    # Input row
    with gr.Row():
        pdf_input = gr.File(label="Upload Requirements PDF", file_types=[".pdf"])
        fr_input = gr.Textbox(label="Assigned FRs (comma-separated, e.g., FR-1, FR-2)", placeholder="DUMMY DEMO. ONLY INPUT 'FR-1, FR-2'", lines=1)


    # Start + Download buttons stacked
    run_btn = gr.Button("Start Processing")
    download_btn = gr.File(label="Download Final CSV")

    # Progress indicator
    progress_label = gr.Label(label="Current Progress")

    # Middle section: FR viewer
    with gr.Row():
        with gr.Column(scale=1):
            fr_selector = gr.Dropdown(choices=list(dummy_steps.keys()), value="FR-1", label="Select FR to View")

        with gr.Column(scale=3):
            with gr.Tab("Step 1: Atomic Blocks"):
                step1_table = gr.Dataframe()
            with gr.Tab("Step 2: Partitions"):
                step2_table = gr.Dataframe()
            with gr.Tab("Step 3: Boundaries"):
                step3_table = gr.Dataframe()

    # Final compiled table: last row, full-width
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Final Compiled Test Cases")
            final_table = gr.Dataframe(headers=list(final_cases.columns))

    # Handlers
    def update_fr_view(fr_id):
        return (
            dummy_steps[fr_id]["step1"],
            dummy_steps[fr_id]["step2"],
            dummy_steps[fr_id]["step3"]
        )

    fr_selector.change(update_fr_view, inputs=fr_selector, outputs=[step1_table, step2_table, step3_table])
    run_btn.click(
        fn=process_pdfs,
        inputs=[pdf_input, fr_input],
        outputs=[progress_label, final_table, download_btn],
        show_progress="minimal"
    )

if __name__ == "__main__":
    demo.launch()
