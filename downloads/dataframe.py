import json
from pathlib import Path

import pandas as pd

from downloads.paths import FINAL_JSON_PATH


def truncate_text(text, max_length=30):
    """Truncate text to max_length characters with ellipsis, preserving word boundaries when possible."""
    if not text or len(text) <= max_length:
        return text

    truncated = text[:max_length].rstrip()
    last_space = truncated.rfind(" ", max(0, max_length - 10))
    if last_space > max_length // 2:
        truncated = text[:last_space].rstrip()

    return truncated + "..."


def truncate_dataframe_cells(df, max_length=30, exclude_columns=None, custom_lengths=None):
    """Truncate text in all DataFrame cells with customizable lengths per column."""
    if exclude_columns is None:
        exclude_columns = ["FR ID", "Environment", "Test Status (Pass / Fail)"]

    if custom_lengths is None:
        custom_lengths = {
            "Test Case": 40,
            "Steps": 35,
            "Test Data": 25,
            "Precondition": 35,
            "Expected Result": 40,
            "Actual Result": 30,
            "Jira Bug Link": 20,
        }

    df_truncated = df.copy()
    for column in df_truncated.columns:
        if column not in exclude_columns:
            col_max_length = custom_lengths.get(column, max_length)
            df_truncated[column] = df_truncated[column].astype(str).apply(
                lambda x: truncate_text(x, col_max_length)
            )
    return df_truncated


def _empty_results_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "FR ID",
            "Test Case",
            "Precondition",
            "Steps",
            "Test Data",
            "Expected Result",
            "Environment",
            "Actual Result",
            "Test Status (Pass / Fail)",
            "Jira Bug Link",
        ]
    )


def load_final_output_as_dataframe(limit_rows=None, truncate_for_snippet=False):
    """Load final_output.json and convert to pandas DataFrame for display or export."""
    from downloads.ensure import ensure_final_output_json

    ensure_final_output_json()
    if not FINAL_JSON_PATH.exists():
        return _empty_results_dataframe()

    try:
        with open(FINAL_JSON_PATH, "r") as f:
            data = json.load(f)

        rows = []
        for test_suite in data.get("test_suite", []):
            fr_id = test_suite.get("fr_id", "Unknown")
            for test_case in test_suite.get("test_cases", []):
                rows.append(
                    {
                        "FR ID": fr_id,
                        "Test Case": test_case.get("title", ""),
                        "Precondition": test_case.get("precondition", ""),
                        "Steps": test_case.get("steps", ""),
                        "Test Data": test_case.get("test_data", ""),
                        "Expected Result": test_case.get("expected_result", ""),
                        "Environment": test_case.get("environment", ""),
                        "Actual Result": test_case.get("actual_result", ""),
                        "Test Status (Pass / Fail)": test_case.get("status", ""),
                        "Jira Bug Link": test_case.get("jira_bug_link", ""),
                    }
                )

        if not rows:
            return _empty_results_dataframe()

        df = pd.DataFrame(rows)
        if limit_rows:
            df = df.head(limit_rows)
        if truncate_for_snippet:
            df = truncate_dataframe_cells(df, max_length=30)
        return df

    except Exception as e:
        print(f"Error loading final output: {e}")
        return _empty_results_dataframe()
