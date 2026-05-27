import operator
from typing import Annotated, Any, NotRequired, TypedDict


class FRState(TypedDict):
    pdf_name: str
    fr_id: str
    fr_text: str
    step_outputs: NotRequired[dict[int, dict[str, Any]]]
    current_step: NotRequired[int]
    error: NotRequired[str | None]


class BatchState(TypedDict):
    pdf_name: str
    frs: list[dict[str, str]]
    completed_frs: NotRequired[Annotated[list[str], operator.add]]
