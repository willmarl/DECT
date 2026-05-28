"""Ensure outputs/final_output.* exist and contain real pipeline results."""

import json
from pathlib import Path

from downloads.paths import FINAL_CSV_PATH, FINAL_JSON_PATH, ensure_outputs_dir

LOGBOOK_DIR = Path("data/pdf_logbook")


def _final_output_has_results(data: dict) -> bool:
    for suite in data.get("test_suite", []):
        if suite.get("test_cases"):
            return True
    return False


def _load_final_output() -> dict | None:
    if not FINAL_JSON_PATH.is_file():
        return None
    try:
        data = json.loads(FINAL_JSON_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _step8_files_exist() -> bool:
    if not LOGBOOK_DIR.is_dir():
        return False
    return any(LOGBOOK_DIR.rglob("step8.json"))


def rebuild_final_output_from_step8() -> bool:
    """Combine step8 logbooks into outputs/final_output.json (+ CSV)."""
    from core.pipeline import combine_all_step8_files

    try:
        combine_all_step8_files()
    except Exception:
        return False
    data = _load_final_output()
    return data is not None and _final_output_has_results(data)


def ensure_final_output_json() -> Path | None:
    """Valid final_output.json path, rebuilding from step8 when missing or empty."""
    ensure_outputs_dir()
    data = _load_final_output()
    if data and _final_output_has_results(data):
        return FINAL_JSON_PATH
    if _step8_files_exist() and rebuild_final_output_from_step8():
        return FINAL_JSON_PATH
    return None


def ensure_final_output_csv() -> Path | None:
    """Valid final_output.csv path, generated from JSON when needed."""
    json_path = ensure_final_output_json()
    if not json_path:
        return None

    json_mtime = json_path.stat().st_mtime
    if (
        FINAL_CSV_PATH.is_file()
        and FINAL_CSV_PATH.stat().st_size > 0
        and FINAL_CSV_PATH.stat().st_mtime >= json_mtime
    ):
        return FINAL_CSV_PATH

    from downloads.csv import ensure_csv_file

    ok, _message = ensure_csv_file()
    if ok and FINAL_CSV_PATH.is_file():
        return FINAL_CSV_PATH
    return None


def results_download_available() -> bool:
    """Cheap check: valid JSON on disk or step8 outputs that can be combined."""
    data = _load_final_output()
    if data and _final_output_has_results(data):
        return True
    return _step8_files_exist()


def get_json_download_path() -> str | None:
    path = ensure_final_output_json()
    return str(path.resolve()) if path else None


def get_csv_download_path() -> str | None:
    path = ensure_final_output_csv()
    return str(path.resolve()) if path else None
