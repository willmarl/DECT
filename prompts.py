# global system prompt
SYSTEM_PROMPT = """You are a QA assistant.
Your job is to transform functional requirements into QA artifacts step by step.
Never add commentary."""

# step-specific user prompts
EXTRACT_FR = """Extract all Functional Requirements (FRs) visible in this image
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