"""Typed contracts between DocChat reasoning agents and workflow routing."""

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


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
    claim_sources: list["ClaimSource"] = Field(default_factory=list)
    citations: list["SourceCitation"] = Field(default_factory=list)


class ClaimSource(StrictAgentResult):
    """A model-proposed mapping from one answer claim to retrieved chunk IDs."""

    claim: str
    chunk_ids: list[str]


class SourceCitation(StrictAgentResult):
    """A resolved, user-inspectable reference to local retrieved evidence."""

    claim: str
    chunk_id: str | None
    document_id: str | None
    source_name: str | None
    section: str | None
    page: int | None
    available: bool
    message: str | None = None


class ComparisonGrounding(StrictAgentResult):
    """Deterministic current-draft source coverage for a comparison operation."""

    active_source_ids: list[str]
    grounded_source_ids: list[str]
    missing_source_ids: list[str]

    @property
    def active_source_count(self) -> int:
        return len(self.active_source_ids)

    @property
    def grounded_source_count(self) -> int:
        return len(self.grounded_source_ids)

    @property
    def is_complete(self) -> bool:
        return not self.missing_source_ids


class VerificationResult(StrictAgentResult):
    """Common workflow-facing fields for one discriminated verification outcome."""

    supported: bool
    relevant: bool
    unsupported_claims: list[str]
    contradictions: list[str]
    correction_feedback: str

    @classmethod
    def from_model_json(cls, response_text: str):
        try:
            return _VERIFICATION_RESULT_ADAPTER.validate_json(response_text)
        except ValidationError as exc:
            raise StructuredOutputError(
                "Model response did not match the required VerificationResult JSON contract."
            ) from exc

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        """Expose mutually exclusive supported/unsupported states to providers."""
        return _VERIFICATION_RESULT_ADAPTER.json_schema()

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


class SupportedVerificationResult(VerificationResult):
    """A support-confirming result that cannot carry evidence-failure lists."""

    supported: Literal[True]
    unsupported_claims: list[str] = Field(default_factory=list, max_length=0)
    contradictions: list[str] = Field(default_factory=list, max_length=0)


class UnsupportedVerificationResult(VerificationResult):
    """An evidence-failure result that cannot claim support simultaneously."""

    supported: Literal[False]


VerificationOutcome = Annotated[
    Union[SupportedVerificationResult, UnsupportedVerificationResult],
    Field(discriminator="supported"),
]
_VERIFICATION_RESULT_ADAPTER = TypeAdapter(VerificationOutcome)
