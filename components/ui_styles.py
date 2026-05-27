"""Shared Gradio UI CSS and dataframe layout helpers."""

# Gradio 6 dataframes use flex virtual rows (.header-cell / .body-cell), not <table><th>.
# When wrap=True, empty columns size from blank cells and headers get squeezed.
GRADIO_DF_CSS = """
.gradio-container .dect-df .header-cell {
    flex-shrink: 0 !important;
    min-width: max-content !important;
}

.gradio-container .dect-df .header-content {
    min-width: max-content !important;
    overflow: visible !important;
}

.gradio-container .dect-df .header-cell span {
    white-space: nowrap !important;
    overflow-wrap: normal !important;
    word-break: keep-all !important;
    overflow: hidden;
    text-overflow: ellipsis;
}

.gradio-container .dect-df .body-cell span.wrap {
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
}

.gradio-container .dect-df-full .table-wrap,
.gradio-container .dect-df-full .virtual-table-viewport,
.gradio-container .dect-df-full .header-table {
    width: 100% !important;
}
"""

# Column weight hints (px) — same proportions for snippet vs full-width table.
_RESULTS_COL_WEIGHTS = [
    140,  # Document
    80,   # FR ID
    60,   # Test #
    220,  # Test Case
    180,  # Precondition
    220,  # Steps
    140,  # Test Data
    180,  # Expected Result
    110,  # Environment
    120,  # Actual Result (often empty — needs a floor)
    90,   # Status
    120,  # Jira Bug Link (often empty)
]


def _widths_as_percentages(weights: list[int]) -> list[str]:
    """Convert weights to % strings that sum to 100 (fills wide containers)."""
    total = sum(weights)
    pcts = [round(w / total * 1000) / 10 for w in weights]
    pcts[-1] = round((100 - sum(pcts[:-1])) * 10) / 10
    return [f"{p}%" for p in pcts]


# Fixed px: good for the narrow snippet column (scrolls horizontally if needed).
RESULTS_COLUMN_WIDTHS = _RESULTS_COL_WEIGHTS

# Percentages: stretch to full width on the bottom results table (no trailing gap).
RESULTS_COLUMN_WIDTHS_FULL = _widths_as_percentages(_RESULTS_COL_WEIGHTS)
