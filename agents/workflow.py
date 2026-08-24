"""LangGraph orchestration using typed agent contracts for all control flow."""

import logging
from time import perf_counter
from typing import TypedDict
from uuid import uuid4

from langchain.retrievers import EnsembleRetriever
from langchain.schema import Document
from langgraph.graph import END, StateGraph

from config.settings import Settings, settings
from providers.contracts import ChatProvider
from providers.contracts import ProviderError
from retriever.builder import RetrievalError
from retriever.evidence import EvidenceCollectionError, EvidenceIntent

from .contracts import (
    ComparisonGrounding,
    RelevanceResult,
    ResearchResult,
    StructuredOutputError,
    SourceCitation,
    TerminalOutcome,
    VerificationResult,
)
from .citations import evaluate_comparison_grounding, format_citation_report
from .relevance_checker import RelevanceChecker
from .research_agent import ResearchAgent
from .run_trace import RunTrace, RunTraceEvent, TraceStage
from .verification_agent import VerificationAgent

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    question: str
    operation: str | None
    evidence_intent: EvidenceIntent
    documents: list[Document]
    draft_answer: str
    verification_report: str
    retriever: EnsembleRetriever
    verification_retries: int
    correction_feedback: str | None
    draft_for_revision: str | None
    terminal_outcome: TerminalOutcome | None
    relevance_result: RelevanceResult | None
    research_result: ResearchResult | None
    citations: list[SourceCitation]
    comparison_grounding: ComparisonGrounding | None
    verification_result: VerificationResult | None
    structured_error: str
    run_id: str
    trace_started_at: float
    trace_events: list[RunTraceEvent]


class AgentWorkflow:
    def __init__(self, chat_provider: ChatProvider, config: Settings = settings):
        self.researcher = ResearchAgent(chat_provider)
        self.verifier = VerificationAgent(chat_provider)
        self.relevance_checker = RelevanceChecker(chat_provider)
        self.config = config
        self.compiled_workflow = self.build_workflow()

    def build_workflow(self):
        """Create the bounded workflow with typed routing state."""
        workflow = StateGraph(AgentState)
        workflow.add_node("check_relevance", self._check_relevance_step)
        workflow.add_node("mark_out_of_scope", self._mark_out_of_scope_step)
        workflow.add_node("research", self._research_step)
        workflow.add_node("verify", self._verification_step)
        workflow.add_node("record_retry", self._record_retry_step)
        workflow.add_node("mark_verified", self._mark_verified_step)
        workflow.add_node("mark_retry_exhausted", self._mark_retry_exhausted_step)
        workflow.add_node("mark_failure", self._mark_failure_step)

        workflow.set_entry_point("check_relevance")
        workflow.add_conditional_edges(
            "check_relevance",
            self._decide_after_relevance_check,
            {
                "relevant": "research",
                "irrelevant": "mark_out_of_scope",
                "failure": "mark_failure",
            },
        )
        workflow.add_edge("mark_out_of_scope", END)
        workflow.add_conditional_edges(
            "research",
            self._decide_after_research,
            {
                "verify": "verify",
                "re_research": "record_retry",
                "retry_exhausted": "mark_retry_exhausted",
                "failure": "mark_failure",
            },
        )
        workflow.add_conditional_edges(
            "verify",
            self._decide_next_step,
            {
                "re_research": "record_retry",
                "verified": "mark_verified",
                "retry_exhausted": "mark_retry_exhausted",
                "failure": "mark_failure",
            },
        )
        workflow.add_edge("record_retry", "research")
        workflow.add_edge("mark_verified", END)
        workflow.add_edge("mark_retry_exhausted", END)
        workflow.add_edge("mark_failure", END)
        return workflow.compile()

    def full_pipeline(
        self,
        question: str,
        retriever: EnsembleRetriever,
        *,
        evidence_intent: EvidenceIntent = EvidenceIntent.QUESTION,
        operation: str | None = None,
    ):
        trace_started_at = perf_counter()
        run_id = uuid4().hex
        try:
            documents = self._collect_evidence(retriever, evidence_intent, question)
        except EvidenceCollectionError as exc:
            return self._initial_failure_result(run_id, trace_started_at, str(exc))
        except (ProviderError, RetrievalError):
            return self._initial_failure_result(
                run_id, trace_started_at, "Document retrieval was unavailable."
            )
        except Exception:
            # A LangChain retriever is an external integration boundary. Its
            # implementation-specific errors must not become an answer or
            # bypass the safe C08 terminal trace.
            logger.error("Document retrieval invocation failed.")
            return self._initial_failure_result(
                run_id, trace_started_at, "Document retrieval was unavailable."
            )
        logger.info("Retrieved %s relevant documents.", len(documents))
        retrieved_chunk_ids = self._retrieved_chunk_ids(documents)
        initial_state = AgentState(
            question=question,
            operation=operation,
            evidence_intent=evidence_intent,
            documents=documents,
            draft_answer="",
            verification_report="",
            retriever=retriever,
            verification_retries=0,
            correction_feedback=None,
            draft_for_revision=None,
            terminal_outcome=None,
            relevance_result=None,
            research_result=None,
            citations=[],
            comparison_grounding=None,
            verification_result=None,
            structured_error="",
            run_id=run_id,
            trace_started_at=trace_started_at,
            trace_events=[
                RunTraceEvent(
                    stage=TraceStage.RETRIEVAL,
                    elapsed_ms=self._elapsed_ms(trace_started_at),
                    stage_latency_ms=self._elapsed_ms(trace_started_at),
                    retrieved_chunk_ids=retrieved_chunk_ids,
                    attempt=0,
                    route="check_relevance",
                )
            ],
        )
        final_state = self.compiled_workflow.invoke(initial_state)
        relevance_result = final_state["relevance_result"]
        verification_result = final_state["verification_result"]
        comparison_grounding = final_state["comparison_grounding"]
        return {
            "draft_answer": final_state["draft_answer"],
            "verification_report": final_state["verification_report"],
            "verification_retries": final_state["verification_retries"],
            "terminal_outcome": final_state["terminal_outcome"].value,
            # Additive structured values for deterministic evaluation consumers.
            # UI output remains the existing human-readable answer/report/citations.
            "relevance_decision": (
                relevance_result.decision.value if relevance_result is not None else None
            ),
            "verification_result": (
                verification_result.model_dump() if verification_result is not None else None
            ),
            "comparison_grounding": (
                comparison_grounding.model_dump() if comparison_grounding is not None else None
            ),
            "run_trace": RunTrace(
                run_id=final_state["run_id"],
                duration_ms=self._elapsed_ms(final_state["trace_started_at"]),
                events=final_state["trace_events"],
            ).model_dump(mode="json"),
            "citations": [citation.model_dump() for citation in final_state["citations"]],
            "citation_report": format_citation_report(final_state["citations"]),
        }

    def _check_relevance_step(self, state: AgentState) -> dict:
        stage_started_at = perf_counter()
        try:
            if state["evidence_intent"] is EvidenceIntent.QUESTION:
                result = self.relevance_checker.check(
                    question=state["question"],
                    retriever=state["retriever"],
                    k=20,
                )
            else:
                result = self.relevance_checker.check_active_document_evidence(
                    state["documents"], state["evidence_intent"]
                )
        except StructuredOutputError as exc:
            return self._structured_failure(
                state,
                "The relevance model returned malformed structured output.",
                exc,
                TraceStage.RELEVANCE,
                self._elapsed_ms(stage_started_at),
            )
        except ProviderError as exc:
            return self._structured_failure(
                state, "The relevance provider was unavailable.", exc, TraceStage.RELEVANCE,
                self._elapsed_ms(stage_started_at),
            )

        route = "relevant" if result.is_relevant else "irrelevant"
        if result.is_relevant:
            return {
                "relevance_result": result,
                "trace_events": self._append_trace(
                    state,
                    self._trace_event(
                        state,
                        TraceStage.RELEVANCE,
                        relevance_decision=result.decision,
                        route=route,
                        stage_latency_ms=self._elapsed_ms(stage_started_at),
                    ),
                ),
            }
        return {
            "relevance_result": result,
            "draft_answer": (
                "This question is not related to the uploaded document(s), or the "
                "documents do not contain enough information to answer it."
            ),
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.RELEVANCE,
                    relevance_decision=result.decision,
                    route=route,
                    stage_latency_ms=self._elapsed_ms(stage_started_at),
                ),
            ),
        }

    @staticmethod
    def _collect_evidence(retriever, intent: EvidenceIntent, question: str) -> list[Document]:
        collector = getattr(retriever, "collect_evidence", None)
        if callable(collector):
            return list(collector(intent, question).documents)
        if intent is not EvidenceIntent.QUESTION:
            raise EvidenceCollectionError(
                "The active retriever does not support the requested study operation."
            )
        return retriever.invoke(question)

    def _research_step(self, state: AgentState) -> dict:
        stage_started_at = perf_counter()
        correction_feedback = state["correction_feedback"]
        draft_for_revision = state["draft_for_revision"]
        try:
            result = self.researcher.generate(
                state["question"],
                state["documents"],
                intent=state["evidence_intent"],
                correction_feedback=correction_feedback,
                previous_draft=draft_for_revision,
            )
        except StructuredOutputError as exc:
            return self._structured_failure(
                state,
                "The research model returned malformed structured output.",
                exc,
                TraceStage.RESEARCH,
                self._elapsed_ms(stage_started_at),
            )
        except ProviderError as exc:
            return self._structured_failure(
                state, "The research provider was unavailable.", exc, TraceStage.RESEARCH,
                self._elapsed_ms(stage_started_at),
            )
        comparison_grounding = None
        if state["evidence_intent"] is EvidenceIntent.MULTI_DOCUMENT_COMPARISON:
            comparison_grounding = evaluate_comparison_grounding(result.citations, state["documents"])
            if not comparison_grounding.is_complete:
                return {
                    "research_result": result,
                    "draft_answer": result.draft_answer,
                    "draft_for_revision": None,
                    # This draft is not comparison-grounded, so it must not
                    # present a partial source set as a successful comparison.
                    "citations": [],
                    "comparison_grounding": comparison_grounding,
                    # A previous retry may have produced a verification result.
                    # It describes a different draft and must not survive as if it
                    # applied to this incomplete current comparison draft.
                    "verification_result": None,
                    "verification_report": (
                        "**Comparison Grounding:** INCOMPLETE\n"
                        "The current comparison draft did not map evidence from every active source."
                    ),
                    "trace_events": self._append_trace(
                        state,
                        self._trace_event(
                            state,
                            TraceStage.RESEARCH,
                            route="comparison_grounding_incomplete",
                            comparison_grounding=comparison_grounding,
                            correction_feedback_supplied=bool(correction_feedback),
                            draft_revision_supplied=draft_for_revision is not None,
                            stage_latency_ms=self._elapsed_ms(stage_started_at),
                        ),
                    ),
                }
        return {
            "research_result": result,
            "draft_answer": result.draft_answer,
            "draft_for_revision": None,
            "citations": result.citations,
            "comparison_grounding": comparison_grounding,
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.RESEARCH,
                    comparison_grounding=comparison_grounding,
                    correction_feedback_supplied=bool(correction_feedback),
                    draft_revision_supplied=draft_for_revision is not None,
                    stage_latency_ms=self._elapsed_ms(stage_started_at),
                ),
            ),
        }

    def _verification_step(self, state: AgentState) -> dict:
        stage_started_at = perf_counter()
        try:
            result = self.verifier.check(
                state["question"],
                state["draft_answer"],
                state["documents"],
                intent=state["evidence_intent"],
            )
        except StructuredOutputError as exc:
            return self._structured_failure(
                state,
                "The verification model returned malformed structured output.",
                exc,
                TraceStage.VERIFICATION,
                self._elapsed_ms(stage_started_at),
            )
        except ProviderError as exc:
            return self._structured_failure(
                state, "The verification provider was unavailable.", exc, TraceStage.VERIFICATION,
                self._elapsed_ms(stage_started_at),
            )
        route = self._verification_route(state, result)
        return {
            "verification_result": result,
            "verification_report": result.to_human_report(),
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.VERIFICATION,
                    verification_supported=result.supported,
                    verification_relevant=result.relevant,
                    route=route,
                    stage_latency_ms=self._elapsed_ms(stage_started_at),
                ),
            ),
        }

    def _decide_after_relevance_check(self, state: AgentState) -> str:
        if state["terminal_outcome"] == TerminalOutcome.FAILURE:
            return "failure"
        result = state["relevance_result"]
        if result is None:
            return "failure"
        return "relevant" if result.is_relevant else "irrelevant"

    def _decide_after_research(self, state: AgentState) -> str:
        if state["terminal_outcome"] == TerminalOutcome.FAILURE:
            return "failure"
        grounding = state["comparison_grounding"]
        if grounding is not None and not grounding.is_complete:
            return self._comparison_grounding_route(state)
        return "verify"

    def _decide_next_step(self, state: AgentState) -> str:
        if state["terminal_outcome"] == TerminalOutcome.FAILURE:
            return "failure"
        result = state["verification_result"]
        if result is None:
            return "failure"
        return self._verification_route(state, result)

    def _verification_route(self, state: AgentState, result: VerificationResult) -> str:
        if not result.requires_research:
            return "verified"
        if state["verification_retries"] < self.config.MAX_VERIFICATION_RETRIES:
            return "re_research"
        return "retry_exhausted"

    def _comparison_grounding_route(self, state: AgentState) -> str:
        """Reuse the existing bounded C03 research budget for an invalid draft."""
        if state["verification_retries"] < self.config.MAX_VERIFICATION_RETRIES:
            return "re_research"
        return "retry_exhausted"

    def _structured_failure(
        self,
        state: AgentState,
        message: str,
        _: StructuredOutputError,
        stage: TraceStage,
        stage_latency_ms: float,
    ) -> dict:
        return {
            "draft_answer": message,
            "verification_report": f"**Workflow Outcome:** FAILURE\n{message}",
            "terminal_outcome": TerminalOutcome.FAILURE,
            "structured_error": message,
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    stage,
                    route="failure",
                    safe_error=message,
                    stage_latency_ms=stage_latency_ms,
                ),
            ),
        }

    def _initial_failure_result(self, run_id: str, started_at: float, message: str) -> dict:
        event = RunTraceEvent(
            stage=TraceStage.RETRIEVAL,
            elapsed_ms=self._elapsed_ms(started_at),
            stage_latency_ms=self._elapsed_ms(started_at),
            attempt=0,
            route="failure",
            safe_error=message,
        )
        terminal = RunTraceEvent(
            stage=TraceStage.TERMINAL,
            elapsed_ms=self._elapsed_ms(started_at),
            stage_latency_ms=0.0,
            attempt=0,
            terminal_outcome=TerminalOutcome.FAILURE,
            safe_error=message,
        )
        return {
            "draft_answer": message,
            "verification_report": f"**Workflow Outcome:** FAILURE\n{message}",
            "verification_retries": 0,
            "terminal_outcome": TerminalOutcome.FAILURE.value,
            "relevance_decision": None,
            "comparison_grounding": None,
            "verification_result": None,
            "run_trace": RunTrace(
                run_id=run_id, duration_ms=self._elapsed_ms(started_at), events=[event, terminal]
            ).model_dump(mode="json"),
            "citations": [],
            "citation_report": "Citations unavailable: retrieval did not complete.",
        }

    def _mark_out_of_scope_step(self, state: AgentState) -> dict:
        return {
            "terminal_outcome": TerminalOutcome.OUT_OF_SCOPE,
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.TERMINAL,
                    terminal_outcome=TerminalOutcome.OUT_OF_SCOPE,
                ),
            ),
        }

    def _record_retry_step(self, state: AgentState) -> dict:
        next_attempt = state["verification_retries"] + 1
        verification_result = state["verification_result"]
        # A retry caused by incomplete comparison grounding has no new
        # verification result. Clear any prior feedback so it cannot leak into
        # a different current draft. Otherwise replace it with only the most
        # recent typed verifier feedback.
        correction_feedback = (
            verification_result.correction_feedback
            if verification_result is not None and verification_result.requires_research
            else None
        )
        draft_for_revision = (
            state["draft_answer"]
            if verification_result is not None and verification_result.requires_research
            else None
        )
        return {
            "verification_retries": next_attempt,
            "correction_feedback": correction_feedback,
            "draft_for_revision": draft_for_revision,
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.ROUTING,
                    attempt=next_attempt,
                    route="re_research",
                    correction_feedback_supplied=bool(correction_feedback),
                    draft_revision_supplied=draft_for_revision is not None,
                ),
            ),
        }

    def _mark_verified_step(self, state: AgentState) -> dict:
        return {
            "terminal_outcome": TerminalOutcome.VERIFIED,
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.TERMINAL,
                    terminal_outcome=TerminalOutcome.VERIFIED,
                ),
            ),
        }

    def _mark_retry_exhausted_step(self, state: AgentState) -> dict:
        retries = state["verification_retries"]
        grounding = state["comparison_grounding"]
        message = (
            "Comparison grounding was not achieved after "
            f"{retries} allowed re-research attempt(s)."
            if grounding is not None and not grounding.is_complete
            else "Verification was not achieved after "
            f"{retries} allowed re-research attempt(s)."
        )
        return {
            "verification_report": (
                f"{state['verification_report']}\n"
                f"**Workflow Outcome:** RETRY_EXHAUSTED\n{message}"
            ),
            "terminal_outcome": TerminalOutcome.RETRY_EXHAUSTED,
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.TERMINAL,
                    terminal_outcome=TerminalOutcome.RETRY_EXHAUSTED,
                    comparison_grounding=grounding,
                ),
            ),
        }

    def _mark_failure_step(self, state: AgentState) -> dict:
        message = state["structured_error"] or "The workflow could not reach a typed terminal state."
        result = {
            "trace_events": self._append_trace(
                state,
                self._trace_event(
                    state,
                    TraceStage.TERMINAL,
                    terminal_outcome=TerminalOutcome.FAILURE,
                    safe_error=message,
                ),
            )
        }
        if not state["verification_report"]:
            result["verification_report"] = f"**Workflow Outcome:** FAILURE\n{message}"
        return result

    @staticmethod
    def _elapsed_ms(trace_started_at: float) -> float:
        return max(0.0, (perf_counter() - trace_started_at) * 1000)

    @staticmethod
    def _retrieved_chunk_ids(documents: list[Document]) -> list[str]:
        return [
            chunk_id
            for document in documents
            if isinstance((chunk_id := document.metadata.get("chunk_id")), str) and chunk_id
        ]

    def _trace_event(
        self,
        state: AgentState,
        stage: TraceStage,
        *,
        relevance_decision=None,
        attempt: int | None = None,
        verification_supported: bool | None = None,
        verification_relevant: bool | None = None,
        correction_feedback_supplied: bool = False,
        draft_revision_supplied: bool = False,
        comparison_grounding: ComparisonGrounding | None = None,
        route: str | None = None,
        terminal_outcome: TerminalOutcome | None = None,
        safe_error: str | None = None,
        stage_latency_ms: float = 0.0,
    ) -> RunTraceEvent:
        return RunTraceEvent(
            stage=stage,
            elapsed_ms=self._elapsed_ms(state["trace_started_at"]),
            stage_latency_ms=stage_latency_ms,
            retrieved_chunk_ids=self._retrieved_chunk_ids(state["documents"]),
            relevance_decision=relevance_decision,
            attempt=state["verification_retries"] if attempt is None else attempt,
            verification_supported=verification_supported,
            verification_relevant=verification_relevant,
            correction_feedback_supplied=correction_feedback_supplied,
            draft_revision_supplied=draft_revision_supplied,
            active_source_count=(
                comparison_grounding.active_source_count if comparison_grounding is not None else None
            ),
            grounded_source_count=(
                comparison_grounding.grounded_source_count
                if comparison_grounding is not None
                else None
            ),
            missing_source_ids=(
                comparison_grounding.missing_source_ids if comparison_grounding is not None else []
            ),
            route=route,
            terminal_outcome=terminal_outcome,
            safe_error=safe_error,
        )

    @staticmethod
    def _append_trace(state: AgentState, event: RunTraceEvent) -> list[RunTraceEvent]:
        return [*state["trace_events"], event]
