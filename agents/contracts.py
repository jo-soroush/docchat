"""Typed contracts between DocChat reasoning agents and workflow routing."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, ValidationError


class StructuredOutputError(ValueError):
    """Raised when a model response does not match its required agent contract."""


class RelevanceDecision(str, Enum):
    CAN_ANSWER = "CAN_ANSWER"
    PARTIAL = "PARTIAL"
    NO_MATCH = "NO_MATCH"


class TerminalOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    FAILURE = "FAILURE"


class StrictAgentResult(BaseModel):
    """Reject undeclared fields and coercions at the model-output boundary."""

    model_config = ConfigDict(extra="forbid", strict=True)

    @classmethod
    def from_model_json(cls, response_text: str):
        try:
            return cls.model_validate_json(response_text)
        except ValidationError as exc:
            raise StructuredOutputError(
                f"Model response did not match the required {cls.__name__} JSON contract."
            ) from exc


class RelevanceResult(StrictAgentResult):
    decision: RelevanceDecision
    explanation: str

    @property
    def is_relevant(self) -> bool:
        return self.decision in {RelevanceDecision.CAN_ANSWER, RelevanceDecision.PARTIAL}


class ResearchResult(StrictAgentResult):
    draft_answer: str


class VerificationResult(StrictAgentResult):
    supported: bool
    relevant: bool
    unsupported_claims: list[str]
    contradictions: list[str]
    correction_feedback: str

    @property
    def requires_research(self) -> bool:
        return not self.supported or not self.relevant

    def to_human_report(self) -> str:
        """Render display text without making it a workflow control contract."""
        supported = "YES" if self.supported else "NO"
        relevant = "YES" if self.relevant else "NO"
        unsupported_claims = ", ".join(self.unsupported_claims) or "None"
        contradictions = ", ".join(self.contradictions) or "None"
        feedback = self.correction_feedback or "None"
        return (
            f"**Supported:** {supported}\n"
            f"**Unsupported Claims:** {unsupported_claims}\n"
            f"**Contradictions:** {contradictions}\n"
            f"**Relevant:** {relevant}\n"
            f"**Additional Details:** {feedback}\n"
        )
