# Atomic Blocks
step1_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "atomic_blocks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "description": { "type": "string" }
        },
        "required": ["id", "description"]
      }
    }
  },
  "required": ["fr_id", "atomic_blocks"]
}
step1_example = """
Example Input:
FR-1: Only Latin letters. The name must be 2–25 characters. If invalid, show error.

Example Output:
{
  "fr_id": "FR-1",
  "atomic_blocks": [
    { "id": "AB-1", "description": "Input must contain only Latin letters" },
    { "id": "AB-2", "description": "Input must be at least 2 characters long" },
    { "id": "AB-3", "description": "Input must not exceed 25 characters" },
    { "id": "AB-4", "description": "Field is required (cannot be empty)" },
    { "id": "AB-5", "description": "If invalid, highlight red and show 'Invalid entry' error" }
  ]
}
"""

# Partitions
step2_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "partitions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "atomic_block_id": { "type": "string" },
          "valid": { "type": "array", "items": { "type": "string" } },
          "invalid": { "type": "array", "items": { "type": "string" } }
        },
        "required": ["atomic_block_id", "valid", "invalid"]
      }
    }
  },
  "required": ["fr_id", "partitions"]
}
step2_example = """
Example Input:
Atomic Block AB-1: "Only Latin letters"

Example Output:
{
  "fr_id": "FR-1",
  "partitions": [
    {
      "atomic_block_id": "AB-1",
      "valid": ["Latin letters"],
      "invalid": ["Special characters", "Numbers", "Non-Latin letters"]
    }
  ]
}
"""

# Boundaries
step3_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "boundaries": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "atomic_block_id": { "type": "string" },
          "cases": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "label": { "type": "string" },
                "example": { "type": "string" }
              },
              "required": ["label", "example"]
            }
          }
        },
        "required": ["atomic_block_id", "cases"]
      }
    }
  },
  "required": ["fr_id", "boundaries"]
}
step3_example = """
Example Input:
Atomic Block AB-2: "Length between 2 and 25 characters"

Example Output:
{
  "fr_id": "FR-1",
  "boundaries": [
    {
      "atomic_block_id": "AB-2",
      "cases": [
        { "label": "Invalid (<2 chars)", "example": "B" },
        { "label": "Boundary (2 chars)", "example": "Li" },
        { "label": "Valid (3–24 chars)", "example": "Alexandra" },
        { "label": "Boundary (25 chars)", "example": "ElizabethMargaretJohnsons" },
        { "label": "Invalid (>25 chars)", "example": "ChristopherAlexanderWilliam" }
      ]
    }
  ]
}
"""

# Test values
step4_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "test_values": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "atomic_block_id": { "type": "string" },
          "value": { "type": "string" },
          "partition_label": { "type": "string" }
        },
        "required": ["atomic_block_id", "value"]
      }
    }
  },
  "required": ["fr_id", "test_values"]
}
step4_example = """
Example Input:
Partitions + Boundaries for AB-1 and AB-2

Example Output:
{
  "fr_id": "FR-1",
  "test_values": [
    { "atomic_block_id": "AB-1", "partition_label": "Valid", "value": "Lula" },
    { "atomic_block_id": "AB-1", "partition_label": "Invalid", "value": "!@#" },
    { "atomic_block_id": "AB-1", "partition_label": "Invalid", "value": "123" },
    { "atomic_block_id": "AB-1", "partition_label": "Invalid", "value": "愛している" },
    { "atomic_block_id": "AB-2", "partition_label": "Boundary", "value": "Li" },
    { "atomic_block_id": "AB-2", "partition_label": "Valid", "value": "Alexandra" },
    { "atomic_block_id": "AB-2", "partition_label": "Invalid", "value": "ChristopherAlexanderWilliam" }
  ]
}
"""

# Unified list
step5_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "values": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["fr_id", "values"]
}
step5_example = """
Example Input:
Collected test values from AB-1 and AB-2

Example Output:
{
  "fr_id": "FR-1",
  "values": [
    "Lula",
    "!@#",
    "123",
    "愛している",
    "Li",
    "Alexandra",
    "ChristopherAlexanderWilliam"
  ]
}
"""

# Deduped list
step6_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "deduped_values": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["fr_id", "deduped_values"]
}
step6_example = """
Example Input:
["Lula", "!@#", "123", "Lula", "Alexandra", "123"]

Example Output:
{
  "fr_id": "FR-1",
  "deduped_values": [
    "Lula",
    "!@#",
    "123",
    "Alexandra"
  ]
}
"""

# Organized Test Data
step7_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "organized_data": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "feature": { "type": "string" },
          "equivalence_class": { "type": "string" },
          "boundary_values": { "type": "array", "items": { "type": "string" } },
          "test_values_for_class": { "type": "array", "items": { "type": "string" } },
          "test_values_for_boundaries": { "type": "array", "items": { "type": "string" } }
        },
        "required": ["feature", "equivalence_class", "test_values_for_class"]
      }
    }
  },
  "required": ["fr_id", "organized_data"]
}
step7_example = """
Example Input:
Deduped test values + partitions/boundaries

Example Output:
{
  "fr_id": "FR-1",
  "organized_data": [
    {
      "feature": "First name field",
      "equivalence_class": "<2 characters (invalid)",
      "boundary_values": ["1", "2", "3", "24", "25", "26"],
      "test_values_for_class": ["B"],
      "test_values_for_boundaries": ["B", "Li", "Ali", "ChristopherAlexanderWill", "ElizabethMargaretJohnsons", "ChristopherAlexanderWilliam"]
    }
  ]
}
"""

# Test Cases
step8_schema = {
  "type": "object",
  "properties": {
    "fr_id": { "type": "string" },
    "test_cases": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "precondition": { "type": "string" },
          "steps": { "type": "string" },
          "test_data": { "type": "string" },
          "expected_result": { "type": "string" },
          "environment": { "type": "string" },
          "actual_result": { "type": "string" },
          "status": { "type": "string", "enum": ["Pass", "Fail", "Not Executed"] },
          "jira_bug_link": { "type": "string" }
        },
        "required": ["title", "steps", "test_data", "expected_result"]
      }
    }
  },
  "required": ["fr_id", "test_cases"]
}
step8_example = """
Example Input:
Organized test data

Example Output:
{
  "fr_id": "FR-1",
  "test_cases": [
    {
      "title": "Verify the user can enter only Latin characters (2-25 characters)",
      "precondition": "User is on homepage, first name field is empty.",
      "steps": "Enter only Latin characters (2-25 chars).",
      "test_data": "Lula",
      "expected_result": "Latin characters are accepted.",
      "environment": "Test Environment",
      "actual_result": "",
      "status": "Not Executed",
      "jira_bug_link": ""
    },
    {
      "title": "Verify the user cannot enter numbers",
      "precondition": "User is on homepage, first name field is empty.",
      "steps": "Enter numbers.",
      "test_data": "123",
      "expected_result": "Numbers are not accepted.",
      "environment": "Test Environment",
      "actual_result": "",
      "status": "Not Executed",
      "jira_bug_link": ""
    }
  ]
}
"""