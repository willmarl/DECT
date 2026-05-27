import json
from datetime import datetime, timezone
from pathlib import Path

from core.io import pdf_stem


def status_dir(pdf_name: str) -> Path:
    return Path(f"data/pdf_logbook/{pdf_stem(pdf_name)}/.status")


def set_fr_status(
    pdf_name: str,
    fr_id: str,
    step: int,
    phase: str,
    message: str = "",
) -> None:
    """Write per-FR status (parallel-safe: one file per FR)."""
    directory = status_dir(pdf_name)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "fr_id": fr_id,
        "step": step,
        "phase": phase,
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    (directory / f"{fr_id}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    write_pipeline_status_summary(pdf_name)


def read_fr_status(pdf_name: str, fr_id: str) -> dict | None:
    path = status_dir(pdf_name) / f"{fr_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_batch_status(pdf_name: str, fr_ids: list[str] | None = None) -> str:
    """Aggregate per-FR status into a single human-readable line."""
    if fr_ids:
        statuses = [read_fr_status(pdf_name, fr_id) for fr_id in fr_ids]
        statuses = [s for s in statuses if s]
    else:
        directory = status_dir(pdf_name)
        statuses = []
        if directory.exists():
            for path in directory.glob("*.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        statuses.append(json.load(f))
                except (json.JSONDecodeError, OSError):
                    pass

    if not statuses:
        return ""

    total = len(statuses)
    done = sum(1 for s in statuses if s.get("phase") == "done")
    errors = sum(1 for s in statuses if s.get("phase") == "error")
    running = [s for s in statuses if s.get("phase") == "running"]

    if done == total:
        return f"Completed {done}/{total} FRs"
    if errors:
        msg = f"{done}/{total} FRs done, {errors} error(s)"
    else:
        msg = f"{done}/{total} FRs done"

    if running:
        r = running[0]
        msg += f" | {r.get('fr_id', '?')} step {r.get('step', '?')}/8"
    return msg


def write_pipeline_status_summary(pdf_name: str | None = None) -> None:
    """Coarse summary for backward compatibility with pipeline_status.txt."""
    status_file = Path("pipeline_status.txt")
    if pdf_name:
        summary = get_batch_status(pdf_name)
        if summary:
            status_file.write_text(summary, encoding="utf-8")
    elif status_file.exists():
        pass


def write_pipeline_status(message: str) -> None:
    """Write a global status message (used at batch start/end)."""
    try:
        Path("pipeline_status.txt").write_text(message, encoding="utf-8")
    except OSError:
        pass
