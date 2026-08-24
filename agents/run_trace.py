"""Safe typed observability contracts for one DocChat workflow run."""

from enum import Enum

from pydantic import Field

from .contracts import RelevanceDecision, StrictAgentResult, TerminalOutcome


class TraceStage(str, Enum):
    RETRIEVAL = "RETRIEVAL"
    RELEVANCE = "RELEVANCE"
    RESEARCH = "RESEARCH"
    VERIFICATION = "VERIFICATION"
    ROUTING = "ROUTING"
    TERMINAL = "TERMINAL"


class RunTraceEvent(StrictAgentResult):
    """One safe, content-free event in a workflow run."""

    stage: TraceStage
    elapsed_ms: float = Field(ge=0)
    stage_latency_ms: float = Field(ge=0)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    relevance_decision: RelevanceDecision | None = None
    attempt: int = Field(ge=0)
    verification_supported: bool | None = None
    verification_relevant: bool | None = None
    correction_feedback_supplied: bool = False
    draft_revision_supplied: bool = False
    active_source_count: int | None = Field(default=None, ge=0)
    grounded_source_count: int | None = Field(default=None, ge=0)
    missing_source_ids: list[str] = Field(default_factory=list)
    route: str | None = None
    terminal_outcome: TerminalOutcome | None = None
    safe_error: str | None = None


class RunTrace(StrictAgentResult):
    """Inspectable workflow trace without user content, prompts, or raw exceptions."""

    run_id: str
    duration_ms: float = Field(ge=0)
    events: list[RunTraceEvent] = Field(default_factory=list)
