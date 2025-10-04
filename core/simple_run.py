from .pipeline import run_pipeline_for_pdf, combine_all_step8_files
import json

# Load the selected tasks
with open("data/selected_tasks.json", "r") as f:
    selected_tasks = json.load(f)

# Process each PDF with its FRs
for pdf_name in selected_tasks:
    frs_list = selected_tasks[pdf_name]
    run_pipeline_for_pdf(pdf_name, frs_list)

# After processing all PDFs and FRs, combine all step8 files
print("\n" + "="*50)
print("COMBINING ALL STEP8 FILES INTO FINAL OUTPUT")
print("="*50)
final_output_path = combine_all_step8_files()