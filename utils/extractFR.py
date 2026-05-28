from pathlib import Path
import base64
import json

from rich import print

from utils.prompts import EXTRACTED_FR
from llm_client import get_image_llm
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, SystemMessage

SYSTEM_PROMPT = EXTRACTED_FR["system_prompt"]
USER_PROMPT = EXTRACTED_FR["user_prompt"]


def extractFRfromImage():
    """Blocking extraction (legacy entry point)."""
    for _msg, done in extract_fr_from_images_with_progress():
        if done:
            return


def extract_fr_from_images_with_progress():
    """
    Yield (detail_message, is_complete) while extracting FRs from input images.
    """
    from core.status import append_status_log

    file_path_input = "inputs"
    path = Path(file_path_input)
    if not path.is_dir():
        raise ValueError(f"Path {file_path_input} is not a directory.")

    folders = sorted(p for p in path.iterdir() if p.is_dir())
    if not folders:
        yield "No image folders found under inputs/", True
        return

    llm = get_image_llm()
    parser = JsonOutputParser()
    chain = llm | parser
    total = len(folders)

    for idx, pdf_folder in enumerate(folders, 1):
        from core.status import is_pdf_cancel_requested

        if is_pdf_cancel_requested():
            yield "PDF processing stopped by user", True
            return
        append_status_log(f"Reading images for {pdf_folder.name} ({idx}/{total})")
        yield f"Reading images for {pdf_folder.name} ({idx}/{total})", False

        content = [{"type": "text", "text": USER_PROMPT}]
        images = sorted(pdf_folder.iterdir(), key=lambda p: p.name)

        for img_idx, img in enumerate(images, 1):
            print("Found image:", img)
            with open(img, "rb") as f:
                img_bytes = f.read()
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_base64}"},
            })
            if img_idx == 1 or img_idx == len(images):
                yield (
                    f"{pdf_folder.name}: loaded page {img_idx}/{len(images)}",
                    False,
                )

        append_status_log(
            f"Calling vision LLM for {pdf_folder.name} ({len(images)} pages)"
        )
        yield (
            f"Vision LLM parsing {pdf_folder.name} ({len(images)} pages)...",
            False,
        )

        if is_pdf_cancel_requested():
            yield "PDF processing stopped by user", True
            return

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=content),  # type: ignore[arg-type]
        ]

        try:
            response = chain.invoke(messages)
        except Exception as e:
            print(f"Error with JSON parsing, trying raw response: {e}")
            raw_response = llm.invoke(messages)
            try:
                raw_content = raw_response.content
                if isinstance(raw_content, str):
                    response = json.loads(raw_content)
                else:
                    print(f"Unexpected content type: {type(raw_content)}")
                    yield f"Failed to parse response for {pdf_folder.name}", False
                    continue
            except json.JSONDecodeError:
                print(f"Failed to parse JSON from raw response: {raw_content}")
                yield f"JSON parse failed for {pdf_folder.name}", False
                continue

        output_dir = Path("data/extractedFR")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{pdf_folder.stem}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(response, indent=2))

        req_count = len(response.get("requirements", []))
        append_status_log(f"Saved {req_count} FR(s) to {output_path.name}")
        print(f"Wrote output to {output_path}")
        yield (
            f"Saved {req_count} requirement(s) from {pdf_folder.name}",
            False,
        )

    yield "FR extraction complete", True
