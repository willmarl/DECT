from downloads.dataframe import load_final_output_as_dataframe
from downloads.ensure import get_csv_download_path
from downloads.paths import ERROR_FILENAME, FINAL_JSON_PATH, ensure_outputs_dir


def ensure_csv_file() -> tuple[bool, str]:
    """Generate final_output.csv from final_output.json if possible."""
    if not FINAL_JSON_PATH.exists():
        return False, "JSON file not found"

    try:
        df = load_final_output_as_dataframe(limit_rows=None, truncate_for_snippet=False)
        if df.empty:
            return False, "No data to export to CSV"

        from downloads.paths import FINAL_CSV_PATH

        df.to_csv(FINAL_CSV_PATH, index=False, encoding="utf-8")
        return True, f"CSV generated successfully: {FINAL_CSV_PATH}"
    except Exception as e:
        return False, f"Error generating CSV: {e}"


def prepare_csv_download() -> str:
    """Return filepath for gr.DownloadButton (single-click download when value is pre-set)."""
    path = get_csv_download_path()
    if path:
        return path

    outputs_dir = ensure_outputs_dir()
    error_file = outputs_dir / ERROR_FILENAME
    error_file.write_text("Error: could not generate CSV from results.")
    return str(error_file.resolve())
