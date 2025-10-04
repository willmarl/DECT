from rich import print
from pathlib import Path
import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from utils.prompts import EXTRACTED_FR
LLM_MODEL = str(os.getenv("OPENAI_MODEL"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# System prompt for consistency
SYSTEM_PROMPT = EXTRACTED_FR["system_prompt"]

# Template for user prompt
USER_PROMPT = EXTRACTED_FR["user_prompt"]


def extractFRfromImage():
    prompt = USER_PROMPT
    filePathInput = "inputs"

    # base system + text prompt
    base_messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    path = Path(filePathInput)
    if not path.is_dir():
        raise ValueError(f"Path {filePathInput} is not a directory.")

    for pdfFolder in path.iterdir():
        print("Searching folder:", pdfFolder)

        # Start one user message for the whole folder
        content = [
            {"type": "text", "text": "Please extract the FR from these images:"}
        ]

        for img in pdfFolder.iterdir():
            print("Found image:", img)
            with open(img, "rb") as f:
                img_bytes = f.read()
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")

            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
            }) # type: ignore

        # Build full message set
        messages = base_messages.copy()
        messages.append({"role": "user", "content": content})

        print(f"Done collecting {len(content)-1} images from {pdfFolder}, sending to LLM...")

        response = ask_gpt(messages)

        raw_json = response.choices[0].message.content # type: ignore
        jsonOutput = json.loads(raw_json)  # type: ignore

        fileName = f"{pdfFolder.stem}.json"
        outputDir = Path("data/extractedFR")
        outputDir.mkdir(parents=True, exist_ok=True)
        outputPath = outputDir / fileName

        with open(outputPath, "w", encoding="utf-8") as f:
            f.write(json.dumps(jsonOutput, indent=2))

        print(f"Wrote output to {outputPath}")

from utils.mockData import fakeResponse2
def ask_gpt(messages):
    return fakeResponse2 # for testing without API calls
    return client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        response_format={"type": "json_object"}  # forces JSON-only output
    )