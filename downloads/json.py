from downloads.ensure import get_json_download_path
from downloads.paths import ERROR_FILENAME, ensure_outputs_dir


def prepare_json_download() -> str:
    """Return filepath for gr.DownloadButton (single-click download when value is pre-set)."""
    path = get_json_download_path()
    if path:
        return path

    outputs_dir = ensure_outputs_dir()
    error_file = outputs_dir / ERROR_FILENAME
    error_file.write_text(
        "Error: no results found. Run the pipeline or ensure step8 outputs exist."
    )
    return str(error_file.resolve())
