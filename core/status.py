import json
import re
from datetime import datetime, timezone
from pathlib import Path

from core.io import pdf_stem

APP_STATUS_FILE = Path("data/app_status.json")
PIPELINE_STATUS_FILE = Path("pipeline_status.txt")
MAX_LOG_LINES = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_app_status() -> dict:
    if not APP_STATUS_FILE.exists():
        return {}
    try:
        with open(APP_STATUS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_app_status(data: dict) -> None:
    APP_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    APP_STATUS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_status_log(message: str, *, detail: str = "") -> None:
    """Append a timestamped line to the rolling activity log."""
    data = _load_app_status()
    log = data.get("log", [])
    log.append(f"{datetime.now().strftime('%H:%M:%S')} — {message}")
    if detail:
        log.append(f"           {detail}")
    data["log"] = log[-MAX_LOG_LINES:]
    _save_app_status(data)


def format_detail_log(data: dict | None = None) -> str:
    """Multi-line activity log for the collapsible detail panel."""
    if data is None:
        data = _load_app_status()
    log = data.get("log", [])
    if not log:
        return "No activity yet."
    return "\n".join(log[-MAX_LOG_LINES:])


def _find_running_fr() -> tuple[str, str, int, str] | None:
    """Return (pdf_name, fr_id, step, message) for a currently running FR, if any."""
    logbook_base = Path("data/pdf_logbook")
    if not logbook_base.exists():
        return None
    for pdf_dir in sorted(logbook_base.iterdir()):
        if not pdf_dir.is_dir() or pdf_dir.name.startswith("."):
            continue
        for fr_dir in sorted(pdf_dir.iterdir()):
            if not fr_dir.is_dir() or not fr_dir.name.startswith("FR-"):
                continue
            st = read_fr_status(pdf_dir.name, fr_dir.name)
            if st and st.get("phase") == "running":
                return (
                    pdf_dir.name,
                    fr_dir.name,
                    int(st.get("step", 0)),
                    st.get("message", ""),
                )
    return None


def format_simple_status(data: dict | None = None) -> str:
    """One-line emoji status for the main UI."""
    if data is None:
        data = _load_app_status()
    if not data:
        return "✅ Ready — upload a PDF to begin"

    if data.get("simple"):
        return data["simple"]

    phase = data.get("phase", "idle")
    message = data.get("message", "")
    detail = data.get("detail", "")
    active = data.get("active", False)
    ml = message.lower()

    if phase == "error":
        return f"❌ {message}"

    if phase == "upload":
        if message.startswith("Received "):
            names = message.replace("Received ", "", 1)
            return f"📄 PDF uploaded — {names}"
        return f"📄 {message}"

    if phase == "idle":
        if "results ready" in ml:
            return f"📥 {message}"
        if "processed successfully" in ml:
            return "✅ PDF processed — select tasks and click Run"
        if message and message != "Ready to process PDFs":
            return f"✅ {message}"
        return "✅ Ready — upload a PDF to begin"

    if phase == "pdf" and active:
        if "clearing" in ml:
            return "🗑️ Preparing files…"
        if "converting" in ml:
            return f"🖼️ Converting to images — {detail}" if detail else "🖼️ Converting PDF to images…"
        if "saving page" in ml or "page images" in ml:
            return f"🖼️ Saving page images — {detail}" if detail else "🖼️ Saving page images…"
        if "extracting" in ml:
            return f"🔍 Extracting requirements — {detail}" if detail else "🔍 Extracting requirements…"
        if "vision" in ml or "llm" in ml:
            return f"🤖 LLM reading pages — {detail}" if detail else "🤖 LLM reading document pages…"
        return f"⚙️ {message}" + (f" — {detail}" if detail else "")

    if phase == "pipeline" and active:
        running = _find_running_fr()
        if running:
            _pdf, fr_id, step, _msg = running
            if step:
                return f"🧪 Running {fr_id} — step {step}/8"
            return f"🧪 Running {fr_id}"
        if "preparing" in ml:
            return "🚀 Preparing analysis…"
        if "starting" in ml:
            return "🚀 Starting test pipeline…"
        if "finished" in ml or "complete" in ml:
            return f"✅ {message}"
        match = re.search(r"(\d+)/(\d+)\s*FR", message + " " + detail)
        if match:
            return f"🧪 Pipeline — {match.group(1)}/{match.group(2)} FRs complete"
        if detail and detail.startswith("FR-"):
            fr_part = detail.split(":")[0].strip()
            return f"🧪 Running {fr_part}"
        return f"🧪 {message}" if message else "🧪 Running test pipeline…"

    if phase in ("pdf", "pipeline") and not active:
        return "✅ Ready — upload a PDF to begin"

    return f"ℹ️ {message}" if message else "✅ Ready — upload a PDF to begin"


def get_status_ui() -> tuple[str, str]:
    """Return (simple_markdown, detail_log) for Gradio status widgets."""
    app = _resolve_display_state()
    simple = format_simple_status(app)
    detail = format_detail_log(app)
    return simple, detail


def _resolve_display_state() -> dict:
    """Pick app status dict to show (handles stale inactive runs)."""
    app = _load_app_status()
    phase = app.get("phase", "idle")
    active = app.get("active", False)

    if phase in ("pdf", "pipeline") and not active:
        return {
            **app,
            "phase": "idle",
            "message": "Ready to process PDFs",
            "detail": "",
            "simple": "✅ Ready — upload a PDF to begin",
        }

    if phase == "pipeline" and active:
        running = _find_running_fr()
        if running:
            _pdf, fr_id, step, msg = running
            app = dict(app)
            app["simple"] = (
                f"🧪 Running {fr_id} — step {step}/8"
                if step
                else f"🧪 Running {fr_id}"
            )

    return app


def set_app_status(
    phase: str,
    message: str,
    detail: str = "",
    *,
    also_log: bool = True,
    active: bool | None = None,
    simple: str | None = None,
) -> None:
    """Update global UI status (PDF upload, pipeline, idle)."""
    data = _load_app_status()
    log = data.get("log", [])
    if also_log and message:
        log.append(f"{datetime.now().strftime('%H:%M:%S')} — {message}")
        if detail and phase in ("pdf", "pipeline"):
            log.append(f"           {detail}")
    if active is None:
        active = phase in ("pdf", "pipeline")
    data.update({
        "phase": phase,
        "message": message,
        "detail": detail,
        "active": active,
        "updated_at": _now_iso(),
        "log": log[-MAX_LOG_LINES:],
    })
    if simple is not None:
        data["simple"] = simple
    else:
        data["simple"] = format_simple_status(data)
    _save_app_status(data)


def note_files_uploaded(filenames: list[str]) -> None:
    """User uploaded PDF(s) but has not clicked Process PDF yet."""
    if not filenames:
        clear_app_status()
        return
    if len(filenames) == 1:
        simple = f"📄 PDF uploaded — {filenames[0]}"
        msg = f"Received {filenames[0]}"
    else:
        simple = f"📄 PDF uploaded — {len(filenames)} files"
        msg = f"Received {len(filenames)} files: {', '.join(filenames)}"
    set_app_status(
        "upload",
        msg,
        'Click "1. Process PDF" to convert pages and extract requirements.',
        also_log=True,
        active=False,
        simple=simple,
    )


def clear_app_status(
    message: str = "Ready to process PDFs",
    *,
    keep_log: bool = False,
) -> None:
    data = {
        "phase": "idle",
        "message": message,
        "detail": "",
        "active": False,
        "simple": "✅ Ready — upload a PDF to begin",
        "updated_at": _now_iso(),
        "log": _load_app_status().get("log", []) if keep_log else [],
    }
    _save_app_status(data)
    try:
        PIPELINE_STATUS_FILE.write_text(data["simple"], encoding="utf-8")
    except OSError:
        pass


def format_app_status(data: dict | None = None) -> str:
    """Legacy combined format (simple + log)."""
    simple, detail = get_status_ui() if data is None else (
        format_simple_status(data),
        format_detail_log(data),
    )
    return f"{simple}\n\n---\n\n{detail}"


def get_app_status_display() -> str:
    return format_app_status()


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
        "updated_at": _now_iso(),
    }
    (directory / f"{fr_id}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    if phase == "running" and step:
        simple = f"🧪 Running {fr_id} — step {step}/8"
    elif phase == "done" and step == 8:
        simple = f"✅ {fr_id} complete"
    elif phase == "error":
        simple = f"❌ {fr_id} failed"
    else:
        simple = f"🧪 Running {fr_id}"

    set_app_status(
        "pipeline",
        get_batch_status(pdf_name, None) or f"Running pipeline for {pdf_name}",
        "",
        also_log=False,
        active=True,
        simple=simple,
    )
    append_status_log(f"{fr_id} — {message or f'step {step}/8 ({phase})'}")


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
        parts = []
        for r in running[:3]:
            rid = r.get("fr_id", "?")
            step = r.get("step", "?")
            rmsg = r.get("message", "")
            parts.append(f"{rid} step {step}/8" + (f" ({rmsg})" if rmsg else ""))
        msg += " | " + "; ".join(parts)
    return msg


def write_pipeline_status(message: str) -> None:
    """Write pipeline message and sync app status."""
    append_status_log(message)
    data = _load_app_status()
    data.setdefault("log", [])
    if data.get("phase") == "pipeline" and data.get("active"):
        data["simple"] = format_simple_status(data)
        _save_app_status(data)
    try:
        PIPELINE_STATUS_FILE.write_text(
            data.get("simple", message), encoding="utf-8"
        )
    except OSError:
        pass


def get_combined_status_display() -> str:
    """Backward-compatible single string (simple line only)."""
    return get_status_ui()[0]
