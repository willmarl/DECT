# Adding a download format

Source of truth: `outputs/final_output.json` (see `downloads/paths.py` → `FINAL_JSON_PATH`).

Tabular exports should use `downloads/dataframe.py` → `load_final_output_as_dataframe(limit_rows=None, truncate_for_snippet=False)` — do not duplicate JSON parsing.

Each format = one module under `downloads/` with a `prepare_<format>_download() -> str` returning an absolute filepath.

UI uses `gr.DownloadButton` with `value=<path>` pre-set (see `get_*_download_path()` in `downloads/ensure.py`). Do **not** wire `.click(fn, outputs=button)` — that needs two clicks. Do **not** include download buttons in timer poll outputs (resets `value`).

## Layout

```
downloads/
  paths.py          # OUTPUTS_DIR, FINAL_* paths, ensure_outputs_dir()
  dataframe.py      # JSON → pandas (shared by CSV + UI snippet)
  json.py           # reference: pass-through download
  csv.py            # reference: generate file then download
  __init__.py       # re-export prepare_* functions
  ADDING_A_FORMAT.md
```

## Checklist (example: `xlsx`)

### 1. `downloads/paths.py`

```python
FINAL_XLSX_PATH = OUTPUTS_DIR / "final_output.xlsx"
```

### 2. `downloads/xlsx.py`

Pattern A — file already exists or is trivial (like `json.py`):

```python
from downloads.paths import ERROR_FILENAME, FINAL_JSON_PATH, FINAL_XLSX_PATH, ensure_outputs_dir

def prepare_xlsx_download() -> str:
    outputs_dir = ensure_outputs_dir()
    if not FINAL_JSON_PATH.exists():
        error_file = outputs_dir / ERROR_FILENAME
        error_file.write_text("Error: final_output.json not found. Please run the analysis first.")
        return str(error_file.resolve())
    if FINAL_XLSX_PATH.exists():
        return str(FINAL_XLSX_PATH.resolve())
    # ... build xlsx, write FINAL_XLSX_PATH, then return str(FINAL_XLSX_PATH.resolve())
    error_file = outputs_dir / ERROR_FILENAME
    error_file.write_text("Error: could not generate XLSX from results.")
    return str(error_file.resolve())
```

Pattern B — generate on demand (like `csv.py`):

- `ensure_xlsx_file() -> tuple[bool, str]` writes `FINAL_XLSX_PATH`
- `prepare_xlsx_download()` calls it, then same error/success return branches as `csv.py`

Use `ERROR_FILENAME` (`download_error.txt`) for user-facing missing/failed states, not `error.txt`.

### 3. `downloads/__init__.py`

```python
from downloads.xlsx import prepare_xlsx_download

__all__ = [..., "prepare_xlsx_download"]
```

### 4. `components/top.py`

**Import**

```python
from downloads import prepare_csv_download, prepare_json_download, prepare_xlsx_download
```

**UI** (same row as other download buttons, ~line 247):

```python
downloadXlsxButton = gr.DownloadButton("📥 Download XLSX", interactive=False, size="md")
```

**Init / after pipeline** — set `value` on the button:

```python
gr.DownloadButton("📥 Download XLSX", value=get_xlsx_download_path(), interactive=bool(path), size="md")
```

Add `get_xlsx_download_path()` beside `ensure_final_output_*` in `ensure.py`. Wire into `download_buttons_state()` in `top.py`.

**Enable/disable after pipeline** — extend `download_buttons_update(interactive: bool)` to return one `gr.update(interactive=interactive)` per download button (currently JSON + CSV). Every `*download_buttons_update(...)` unpack site must stay arity-matched.

**`complete_analysis` → `runButton.click(...).then(..., outputs=[...])`** — append `downloadXlsxButton` to `outputs` list (order must match yield tuples).

**`clear_all_and_reset` → `clearButton.click(..., outputs=[...])`** — append `downloadXlsxButton` in the same position as in `complete_analysis` outputs.

Do not re-add zip bundling; one button = one file.

## Conventions

| Item | Rule |
|------|------|
| Function name | `prepare_<format>_download` |
| Module name | `downloads/<format>.py` (lowercase) |
| Output file | `outputs/final_output.<ext>` constant in `paths.py` |
| Missing JSON | Write `outputs/download_error.txt`, return that path |
| Gradio return | `str` absolute path from `Path.resolve()`; set as DownloadButton `value` at init / `download_buttons_state()` |
| Dependencies | Add to `requirements.txt` if new library (e.g. `openpyxl`) |

## Files to grep when wiring UI

- `download_buttons_update`
- `downloadJsonButton` / `downloadCsvButton` (mirror naming: `downloadXlsxButton`)
- `download_buttons_state` / `results_download_available` / `downloads/ensure.py` (rebuild empty JSON from step8; `blocks.load` refreshes button paths)
- `complete_analysis` yields using `*download_buttons_update` or `*download_buttons_state`
- `clear_all_and_reset` return list

## Optional

- Pre-generate in pipeline (`core/pipeline.py`) only if the format must exist before the user clicks; otherwise generate in `ensure_*_file()` on button click (CSV model).
