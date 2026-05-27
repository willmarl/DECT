import json
import threading
import time
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from rich import print

from config import MAX_PARALLEL_FRS
from llm_client import get_llm

_llm_semaphore = threading.Semaphore(MAX_PARALLEL_FRS)

# (input_data_key, template_placeholder_name in utils.prompts user_prompt)
STEP_FORMAT_KEYS: dict[int, list[tuple[str, str]]] = {
    2: [("atomic_blocks", "atomic_blocks")],
    3: [("partitions", "partitions")],
    4: [("partitions", "partitions"), ("boundaries", "boundaries")],
    5: [("test_values", "test_values")],
    6: [("values", "unified_values")],
    7: [("deduped_values", "deduped_values")],
    8: [("organized_data", "organized_data")],
}


def _json_for_prompt(obj: Any) -> str:
    """JSON text safe to embed in a ChatPromptTemplate message (brace-escaped)."""
    return json.dumps(obj, indent=2).replace("{", "{{").replace("}", "}}")


def _build_user_prompt(step_number: int, step_prompt: dict, step_input_data: dict) -> str:
    if step_number == 1:
        return step_prompt["user_prompt"]

    user_text = step_prompt["user_prompt"]
    for data_key, placeholder in STEP_FORMAT_KEYS[step_number]:
        token = "{" + placeholder + "}"
        user_text = user_text.replace(
            token, _json_for_prompt(step_input_data.get(data_key, []))
        )
    return user_text


def invoke_step(
    step_number: int,
    step_prompt: dict,
    step_input_data: dict,
    fr_text: str,
) -> dict:
    """Run one pipeline step via LLM and return parsed JSON."""
    from core.status import append_status_log

    append_status_log(f"LLM step {step_number}: preparing prompt")
    print(f"  Preparing prompt for step {step_number}...")
    start_time = time.time()

    with _llm_semaphore:
        append_status_log(f"LLM step {step_number}: waiting for API slot")
        llm = get_llm()

        if step_number == 1:
            print(f"  Step 1: FR text ({len(fr_text)} chars)")
            prompt = ChatPromptTemplate.from_messages([
                {"role": "system", "content": step_prompt["system_prompt"]},
                {"role": "user", "content": step_prompt["user_prompt"]},
                {"role": "user", "content": fr_text},
            ])
        else:
            user_content = _build_user_prompt(step_number, step_prompt, step_input_data)
            for data_key, _ in STEP_FORMAT_KEYS[step_number]:
                count = len(step_input_data.get(data_key, []))
                print(f"  Step {step_number}: {data_key} count={count}")
            print(f"  User prompt length: {len(user_content)} chars")
            prompt = ChatPromptTemplate.from_messages([
                {"role": "system", "content": step_prompt["system_prompt"]},
                {"role": "user", "content": user_content},
            ])

        chain = prompt | llm | JsonOutputParser()
        append_status_log(f"LLM step {step_number}: calling model")
        print(f"  Invoking LLM for step {step_number}...")
        result = chain.invoke({})

    elapsed = time.time() - start_time
    append_status_log(f"LLM step {step_number}: done ({elapsed:.1f}s)")
    print(f"  Step {step_number} LLM call completed in {elapsed:.1f}s")
    return result
