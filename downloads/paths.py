from pathlib import Path

OUTPUTS_DIR = Path("outputs")
FINAL_JSON_PATH = OUTPUTS_DIR / "final_output.json"
FINAL_CSV_PATH = OUTPUTS_DIR / "final_output.csv"
ERROR_FILENAME = "download_error.txt"


def ensure_outputs_dir() -> Path:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    return OUTPUTS_DIR


def results_download_available() -> bool:
    """True when downloadable results exist (valid JSON or rebuildable step8 files)."""
    from downloads.ensure import results_download_available as _available

    return _available()
