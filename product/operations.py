"""Deterministic study-operation requests routed through the existing workflow."""

from enum import Enum
from typing import Any, Protocol


class OperationInputError(ValueError):
    """Safe validation error for a user-selected research operation."""


class ResearchOperation(str, Enum):
    ASK = "ask"
    SUMMARIZE = "summarize"
    KEY_POINTS = "key_points"
    COMPARE_SOURCES = "compare_sources"
    EXPLAIN_CONCEPT = "explain_concept"
    STUDY_QUESTIONS = "study_questions"


OPERATION_LABELS: dict[ResearchOperation, str] = {
    ResearchOperation.ASK: "Ask",
    ResearchOperation.SUMMARIZE: "Summarize",
    ResearchOperation.KEY_POINTS: "Key Points",
    ResearchOperation.COMPARE_SOURCES: "Compare Sources",
    ResearchOperation.EXPLAIN_CONCEPT: "Explain Concept",
    ResearchOperation.STUDY_QUESTIONS: "Generate Study Questions",
}


class WorkflowRunner(Protocol):
    """The small backend surface the product layer is permitted to call."""

    def full_pipeline(self, question: str, retriever: Any) -> dict: ...


def gradio_operation_choices() -> list[tuple[str, str]]:
    """Return stable labels and values for the Gradio operation selector."""
    return [(OPERATION_LABELS[operation], operation.value) for operation in ResearchOperation]


def build_operation_question(operation_value: str, user_text: str | None) -> str:
    """Convert a product operation into one ordinary, backend-owned question."""
    try:
        operation = ResearchOperation(operation_value)
    except ValueError as exc:
        raise OperationInputError("Select a supported research operation.") from exc

    focus = (user_text or "").strip()
    if operation is ResearchOperation.ASK:
        if not focus:
            raise OperationInputError("Enter a question for Ask.")
        return focus
    if operation is ResearchOperation.SUMMARIZE:
        return _with_optional_focus("Summarize the uploaded document(s).", focus)
    if operation is ResearchOperation.KEY_POINTS:
        return _with_optional_focus("List the key points from the uploaded document(s).", focus)
    if operation is ResearchOperation.COMPARE_SOURCES:
        return _with_optional_focus("Compare the uploaded document sources.", focus)
    if operation is ResearchOperation.EXPLAIN_CONCEPT:
        if not focus:
            raise OperationInputError("Enter a concept to explain.")
        return f"Explain the concept '{focus}' using the uploaded document(s)."
    return _with_optional_focus("Generate study questions from the uploaded document(s).", focus)


def run_operation(
    operation_value: str,
    user_text: str | None,
    workflow: WorkflowRunner,
    retriever: Any,
) -> dict:
    """Dispatch exactly once to the existing verified workflow; do not alter its result."""
    return workflow.full_pipeline(
        question=build_operation_question(operation_value, user_text),
        retriever=retriever,
    )


def _with_optional_focus(instruction: str, focus: str) -> str:
    return f"{instruction} Focus on: {focus}" if focus else instruction
