import json
import utils.schema as s

# Helper to escape braces so ChatPromptTemplate doesn't treat JSON braces as template vars
def _esc_obj(obj: object) -> str:
        # Dump JSON then escape braces by doubling them
        return json.dumps(obj, indent=2).replace("{", "{{").replace("}", "}}")

def _esc_str(text: str) -> str:
        # Escape existing braces in a raw example string
        return text.replace("{", "{{").replace("}", "}}")

EXTRACTED_FR = {
        "system_prompt":"""You are a QA assistant.
Your job is to transform functional requirements into QA artifacts step by step.
Never add commentary.""",
        "user_prompt": """Extract all Functional Requirements (FRs) visible in this image
and return them in the following JSON format:

{
    "requirements": [
        {
            "id": "FR-1",
            "text": "..."
        }
    ]
}

Extract the FR information and return it strictly as JSON.
Do not include any other text, explanations, or formatting.
"""
}

# Step 1: Atomic Blocks
STEP1 = {
    "system_prompt": f"""You are a QA analyst. Break down the given functional requirement
into the smallest independent, testable units called atomic blocks. Each atomic block must describe
exactly one verifiable condition or behavior from the requirement.

Use the following schema and example for formatting your response:
{_esc_obj(s.step1_schema)}
Use the following example as a guide:
{_esc_str(s.step1_example)}
""",
    "user_prompt": """Break down the following requirement into atomic blocks.
Return only valid JSON following the schema and example provided.
"""
}

# Step 2: Partitions
STEP2 = {
    "system_prompt": f"""You are a QA analyst creating equivalence partitions for each atomic block.
For every atomic block, identify valid and invalid input categories.

Use the following schema and example for formatting your response:
{_esc_obj(s.step2_schema)}
Use the following example as a guide:
{_esc_str(s.step2_example)}
""",
    "user_prompt": """Using the atomic blocks from Step 1, identify valid and invalid partitions.
Return only JSON following the schema and example.

Atomic Blocks:
{atomic_blocks}
"""
}

# Step 3: Boundaries
STEP3 = {
    "system_prompt": f"""You are a QA analyst defining boundary values for numeric or range-based
atomic blocks. Identify invalid, boundary, and valid examples for each block.

Use the following schema and example for formatting your response:
{_esc_obj(s.step3_schema)}
Use the following example as a guide:
{_esc_str(s.step3_example)}
""",
    "user_prompt": """Using the partitions from Step 2, define boundary cases for each applicable atomic block.
Return only JSON following the schema and example.

Partitions:
{partitions}
"""
}

# Step 4: Test Values
STEP4 = {
    "system_prompt": f"""You are a QA analyst creating concrete test values for each partition and boundary case.
Generate realistic example inputs for every category.

Use the following schema and example for formatting your response:
{_esc_obj(s.step4_schema)}
Use the following example as a guide:
{_esc_str(s.step4_example)}
""",
    "user_prompt": """Using partitions and boundary cases, produce test values for each atomic block.
Return only JSON following the schema and example.

Partitions:
{partitions}
Boundaries:
{boundaries}
"""
}

# Step 5: Unified List
STEP5 = {
    "system_prompt": f"""You are a QA analyst consolidating test data.
Flatten all test values from previous steps into a single unified list of inputs.

Use the following schema and example for formatting your response:
{_esc_obj(s.step5_schema)}
Use the following example as a guide:
{_esc_str(s.step5_example)}
""",
    "user_prompt": """Combine all test values from previous steps into a unified list.
Return only JSON following the schema and example.

Test Values:
{test_values}
"""
}

# Step 6: Deduped List
STEP6 = {
    "system_prompt": f"""You are a QA analyst cleaning the test data.
Remove duplicates while preserving logical diversity of test cases.

Use the following schema and example for formatting your response:
{_esc_obj(s.step6_schema)}
Use the following example as a guide:
{_esc_str(s.step6_example)}
""",
    "user_prompt": """Remove duplicate test values and output a cleaned list.
Return only JSON following the schema and example.

Unified Test Values:
{unified_values}
"""
}

# Step 7: Organized Test Data
STEP7 = {
    "system_prompt": f"""You are a QA analyst structuring organized test data to simplify
test case generation. Group values by feature, equivalence class, and boundaries.

Use the following schema and example for formatting your response:
{_esc_obj(s.step7_schema)}
Use the following example as a guide:
{_esc_str(s.step7_example)}
""",
    "user_prompt": """Organize the deduped test values into equivalence classes and boundary groupings.
Return only JSON following the schema and example.

Deduped Test Values:
{deduped_values}
"""
}

# Step 8: Test Cases
STEP8 = {
    "system_prompt": f"""You are a QA analyst writing detailed test cases based on the organized data.
Each test case must include title, precondition, steps, data, and expected result.

Use the following schema and example for formatting your response:
{_esc_obj(s.step8_schema)}
Use the following example as a guide:
{_esc_str(s.step8_example)}
""",
    "user_prompt": """Generate detailed test cases using the organized test data.
Return only JSON following the schema and example.

Organized Test Data:
{organized_data}
"""
}
