from .pipeline import run_pipeline_for_pdf, combine_all_step8_files
import json


def main():
    with open("data/selected_tasks.json", encoding="utf-8") as f:
        selected_tasks = json.load(f)

    for pdf_name in selected_tasks:
        frs_list = selected_tasks[pdf_name]
        run_pipeline_for_pdf(pdf_name, frs_list)

    print("\n" + "=" * 50)
    print("COMBINING ALL STEP8 FILES INTO FINAL OUTPUT")
    print("=" * 50)
    final_output_path = combine_all_step8_files()
    return final_output_path


if __name__ == "__main__":
    main()
