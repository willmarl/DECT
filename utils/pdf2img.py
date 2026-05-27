"""
Transform PDFs to images for multimodal LLM extraction (better accuracy than raw PDF text).
"""
from pdf2image import convert_from_bytes
from pathlib import Path
import os

input_folder_name = "inputs"


def fresh_pdf_folders():
    p = Path(input_folder_name)
    if p.exists():
        for folder in p.iterdir():
            for file in folder.iterdir():
                file.unlink()
            folder.rmdir()
    else:
        p.mkdir()


def make_folder(folder_name):
    p = Path(f"{input_folder_name}/{folder_name}")
    p.mkdir()


def pdf_to_images(pdf_bytes):
    """Process uploaded PDFs (blocking). Prefer pdf_to_images_with_progress for UI."""
    success = False
    for _simple, _detail, done in pdf_to_images_with_progress(pdf_bytes):
        success = done
    return success


def pdf_to_images_with_progress(pdf_bytes):
    """
    Yield (simple_status, detail_log, is_complete) while processing PDFs.
    is_complete is True only on the final yield with success/failure.
    """
    from core.status import get_status_ui, set_app_status

    if not pdf_bytes:
        set_app_status(
            "error",
            "No PDF files uploaded",
            "",
            also_log=True,
            active=False,
            simple="❌ No PDF files uploaded",
        )
        yield *get_status_ui(), True
        return

    set_app_status(
        "pdf",
        "Starting PDF processing",
        f"{len(pdf_bytes)} file(s) queued",
        active=True,
        simple=f"⚙️ Processing {len(pdf_bytes)} PDF(s)…",
    )
    yield *_format_pdf_status(), False

    set_app_status(
        "pdf",
        "Clearing previous uploads",
        "Removing old input folders",
        simple="🗑️ Preparing files…",
    )
    yield *_format_pdf_status(), False
    fresh_pdf_folders()

    file_list = []
    for file in pdf_bytes:
        file_list.append(os.path.splitext(os.path.basename(file.name))[0])

    total_pdfs = len(file_list)
    for i, file_name in enumerate(file_list):
        set_app_status(
            "pdf",
            f"Converting PDF to images ({i + 1}/{total_pdfs})",
            f"Document: {file_name}.pdf — rendering pages at 300 DPI",
            simple=f"🖼️ Converting {file_name}.pdf ({i + 1}/{total_pdfs})",
        )
        yield *_format_pdf_status(), False

        make_folder(file_name)
        with open(pdf_bytes[i].name, "rb") as file:
            file_bytes = file.read()

        images = convert_from_bytes(file_bytes, dpi=300)
        page_count = len(images)

        for j, img in enumerate(images):
            set_app_status(
                "pdf",
                f"Saving page images ({i + 1}/{total_pdfs})",
                f"{file_name}.pdf — page {j + 1}/{page_count}",
                simple=f"🖼️ {file_name}.pdf — page {j + 1}/{page_count}",
            )
            if j == 0 or j == page_count - 1 or j % max(1, page_count // 4) == 0:
                yield *_format_pdf_status(), False
            img.save(f"{input_folder_name}/{file_name}/{j + 1}.png", "PNG")

    set_app_status(
        "pdf",
        "Extracting functional requirements",
        "Sending page images to vision LLM (this may take a minute)",
        simple="🔍 Extracting requirements with vision LLM…",
    )
    yield *_format_pdf_status(), False

    from utils.extractFR import extract_fr_from_images_with_progress

    for msg, done in extract_fr_from_images_with_progress():
        if "Vision LLM" in msg or "LLM" in msg:
            simple = f"🤖 {msg}"
        elif "Saved" in msg:
            simple = f"✅ {msg}"
        else:
            simple = f"🔍 {msg}"
        set_app_status("pdf", "Extracting functional requirements", msg, simple=simple)
        yield *_format_pdf_status(), False
        if done:
            break

    set_app_status(
        "idle",
        "PDF processed successfully",
        "Select requirements below, then click Run",
        active=False,
        simple="✅ PDF processed — select tasks and click Run",
    )
    yield *_format_pdf_status(), True


def _format_pdf_status():
    from core.status import get_status_ui
    return get_status_ui()
