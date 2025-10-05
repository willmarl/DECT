from rich import print
from pathlib import Path
import os
import base64
import json
from utils.prompts import EXTRACTED_FR
from llm_client import get_image_llm
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, SystemMessage

llm = get_image_llm()

# System prompt for consistency
SYSTEM_PROMPT = EXTRACTED_FR["system_prompt"]

# Template for user prompt
USER_PROMPT = EXTRACTED_FR["user_prompt"]


def extractFRfromImage():
    filePathInput = "inputs"

    path = Path(filePathInput)
    if not path.is_dir():
        raise ValueError(f"Path {filePathInput} is not a directory.")

    for pdfFolder in path.iterdir():
        print("Searching folder:", pdfFolder)

        # Start one user message for the whole folder
        content = [
            {"type": "text", "text": USER_PROMPT}
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

        print(f"Done collecting {len(content)-1} images from {pdfFolder}, sending to LLM...")

        # Create messages directly
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=content)  # type: ignore
        ]

        # Create simple chain with JSON parser
        parser = JsonOutputParser()
        chain = llm | parser
        
        try:
            response = chain.invoke(messages)
        except Exception as e:
            print(f"Error with JSON parsing, trying raw response: {e}")
            # Fallback to raw response if JSON parsing fails
            raw_response = llm.invoke(messages)
            try:
                content = raw_response.content
                if isinstance(content, str):
                    response = json.loads(content)
                else:
                    print(f"Unexpected content type: {type(content)}")
                    continue
            except json.JSONDecodeError:
                print(f"Failed to parse JSON from raw response: {content}")
                continue

        fileName = f"{pdfFolder.stem}.json"
        outputDir = Path("data/extractedFR")
        outputDir.mkdir(parents=True, exist_ok=True)
        outputPath = outputDir / fileName

        with open(outputPath, "w", encoding="utf-8") as f:
            f.write(json.dumps(response, indent=2))

        print(f"Wrote output to {outputPath}")

# from utils.mockData import fakeResponse2
# def ask_gpt(messages):
#     #return fakeResponse2 # for testing without API calls
#     return client.chat.completions.create(
#         model=LLM_MODEL,
#         messages=messages,
#         response_format={"type": "json_object"}  # forces JSON-only output
#     )