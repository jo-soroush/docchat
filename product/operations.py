"""Deterministic study-operation requests routed through the existing workflow."""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Protocol

from retriever.evidence import EvidenceIntent


class OperationInputError(ValueError):
    """Safe validation error for a user-selected research operation."""


class ResearchOperation(str, Enum):
    ASK = "ask"
    SUMMARIZE = "summarize"
    KEY_POINTS = "key_points"
    COMPARE_SOURCES = "compare_sources"
    EXPLAIN_CONCEPT = "explain_concept"
    STUDY_QUESTIONS = "study_questions"


@dataclass(frozen=True)
class OperationRequest:
    """Validated product intent handed to the workflow as structured state."""

    operation: ResearchOperation
    evidence_intent: EvidenceIntent
    question: str


OPERATION_LABELS: dict[ResearchOperation, str] = {
    ResearchOperation.ASK: "Ask",
    ResearchOperation.SUMMARIZE: "Summarize",
    ResearchOperation.KEY_POINTS: "Key Points",
    ResearchOperation.COMPARE_SOURCES: "Compare Sources",
    ResearchOperation.EXPLAIN_CONCEPT: "Explain Concept",
    ResearchOperation.STUDY_QUESTIONS: "Generate Study Questions",
}

OPERATION_INTENTS: dict[ResearchOperation, EvidenceIntent] = {
    ResearchOperation.ASK: EvidenceIntent.QUESTION,
    ResearchOperation.EXPLAIN_CONCEPT: EvidenceIntent.QUESTION,
    ResearchOperation.SUMMARIZE: EvidenceIntent.DOCUMENT_SYNTHESIS,
    ResearchOperation.KEY_POINTS: EvidenceIntent.DOCUMENT_SYNTHESIS,
    ResearchOperation.STUDY_QUESTIONS: EvidenceIntent.DOCUMENT_SYNTHESIS,
    ResearchOperation.COMPARE_SOURCES: EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
}


class WorkflowRunner(Protocol):
    """The small backend surface the product layer is permitted to call."""

    def full_pipeline(
        self,
        question: str,
        retriever: Any,
        *,
        evidence_intent: EvidenceIntent = EvidenceIntent.QUESTION,
        operation: str | None = None,
    ) -> dict: ...


def gradio_operation_choices() -> list[tuple[str, str]]:
    """Return stable labels and values for the Gradio operation selector."""
    return [(OPERATION_LABELS[operation], operation.value) for operation in ResearchOperation]


def build_operation_question(operation_value: str, user_text: str | None) -> str:
    """Compatibility helper returning the normalized question in an operation request."""
    return build_operation_request(operation_value, user_text).question


def build_operation_request(operation_value: str, user_text: str | None) -> OperationRequest:
    """Validate an operation and preserve its evidence semantics as typed state."""
    try:
        operation = ResearchOperation(operation_value)
    except ValueError as exc:
        raise OperationInputError("Select a supported research operation.") from exc

    focus = (user_text or "").strip()
    if operation is ResearchOperation.ASK:
        if not focus:
            raise OperationInputError("Enter a question for Ask.")
        question = focus
    elif operation is ResearchOperation.SUMMARIZE:
        question = _with_optional_focus("Summarize the uploaded document(s).", focus)
    elif operation is ResearchOperation.KEY_POINTS:
        question = _with_optional_focus("List the key points from the uploaded document(s).", focus)
    elif operation is ResearchOperation.COMPARE_SOURCES:
        question = _with_optional_focus("Compare the uploaded document sources.", focus)
    elif operation is ResearchOperation.EXPLAIN_CONCEPT:
        if not focus:
            raise OperationInputError("Enter a concept to explain.")
        question = f"Explain the concept '{focus}' using the uploaded document(s)."
    else:
        question = _with_optional_focus("Generate study questions from the uploaded document(s).", focus)
    return OperationRequest(
        operation=operation,
        evidence_intent=OPERATION_INTENTS[operation],
        question=question,
    )


def run_operation(
    operation_value: str,
    user_text: str | None,
    workflow: WorkflowRunner,
    retriever: Any,
) -> dict:
    """Dispatch exactly once to the existing verified workflow; do not alter its result."""
    request = build_operation_request(operation_value, user_text)
    return workflow.full_pipeline(
        question=request.question,
        retriever=retriever,
        evidence_intent=request.evidence_intent,
        operation=request.operation.value,
    )


def _with_optional_focus(instruction: str, focus: str) -> str:
    return f"{instruction} Focus on: {focus}" if focus else instruction
