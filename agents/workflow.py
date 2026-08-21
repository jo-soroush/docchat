"""LangGraph orchestration using typed agent contracts for all control flow."""

import logging
from typing import TypedDict

from langchain.retrievers import EnsembleRetriever
from langchain.schema import Document
from langgraph.graph import END, StateGraph

from config.settings import Settings, settings
from providers.contracts import ChatProvider

from .contracts import (
    RelevanceResult,
    ResearchResult,
    StructuredOutputError,
    TerminalOutcome,
    VerificationResult,
)
from .relevance_checker import RelevanceChecker
from .research_agent import ResearchAgent
from .verification_agent import VerificationAgent

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    question: str
    documents: list[Document]
    draft_answer: str
    verification_report: str
    retriever: EnsembleRetriever
    verification_retries: int
    terminal_outcome: TerminalOutcome | None
    relevance_result: RelevanceResult | None
    research_result: ResearchResult | None
    verification_result: VerificationResult | None
    structured_error: str


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
            {"verify": "verify", "failure": "mark_failure"},
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

    def full_pipeline(self, question: str, retriever: EnsembleRetriever):
        documents = retriever.invoke(question)
        logger.info("Retrieved %s relevant documents.", len(documents))
        initial_state = AgentState(
            question=question,
            documents=documents,
            draft_answer="",
            verification_report="",
            retriever=retriever,
            verification_retries=0,
            terminal_outcome=None,
            relevance_result=None,
            research_result=None,
            verification_result=None,
            structured_error="",
        )
        final_state = self.compiled_workflow.invoke(initial_state)
        return {
            "draft_answer": final_state["draft_answer"],
            "verification_report": final_state["verification_report"],
            "verification_retries": final_state["verification_retries"],
            "terminal_outcome": final_state["terminal_outcome"].value,
        }

    def _check_relevance_step(self, state: AgentState) -> dict:
        try:
            result = self.relevance_checker.check(
                question=state["question"],
                retriever=state["retriever"],
                k=20,
            )
        except StructuredOutputError as exc:
            return self._structured_failure(
                "The relevance model returned malformed structured output.", exc
            )

        if result.is_relevant:
            return {"relevance_result": result}
        return {
            "relevance_result": result,
            "draft_answer": (
                "This question is not related to the uploaded document(s), or the "
                "documents do not contain enough information to answer it."
            ),
        }

    def _research_step(self, state: AgentState) -> dict:
        try:
            result = self.researcher.generate(state["question"], state["documents"])
        except StructuredOutputError as exc:
            return self._structured_failure(
                "The research model returned malformed structured output.", exc
            )
        return {"research_result": result, "draft_answer": result.draft_answer}

    def _verification_step(self, state: AgentState) -> dict:
        try:
            result = self.verifier.check(state["draft_answer"], state["documents"])
        except StructuredOutputError as exc:
            return self._structured_failure(
                "The verification model returned malformed structured output.", exc
            )
        return {
            "verification_result": result,
            "verification_report": result.to_human_report(),
        }

    def _decide_after_relevance_check(self, state: AgentState) -> str:
        if state["terminal_outcome"] == TerminalOutcome.FAILURE:
            return "failure"
        result = state["relevance_result"]
        if result is None:
            return "failure"
        return "relevant" if result.is_relevant else "irrelevant"

    def _decide_after_research(self, state: AgentState) -> str:
        return "failure" if state["terminal_outcome"] == TerminalOutcome.FAILURE else "verify"

    def _decide_next_step(self, state: AgentState) -> str:
        if state["terminal_outcome"] == TerminalOutcome.FAILURE:
            return "failure"
        result = state["verification_result"]
        if result is None:
            return "failure"
        if not result.requires_research:
            return "verified"
        if state["verification_retries"] < self.config.MAX_VERIFICATION_RETRIES:
            return "re_research"
        return "retry_exhausted"

    @staticmethod
    def _structured_failure(message: str, _: StructuredOutputError) -> dict:
        return {
            "draft_answer": message,
            "verification_report": f"**Workflow Outcome:** FAILURE\n{message}",
            "terminal_outcome": TerminalOutcome.FAILURE,
            "structured_error": message,
        }

    @staticmethod
    def _mark_out_of_scope_step(_: AgentState) -> dict:
        return {"terminal_outcome": TerminalOutcome.OUT_OF_SCOPE}

    @staticmethod
    def _record_retry_step(state: AgentState) -> dict:
        return {"verification_retries": state["verification_retries"] + 1}

    @staticmethod
    def _mark_verified_step(_: AgentState) -> dict:
        return {"terminal_outcome": TerminalOutcome.VERIFIED}

    @staticmethod
    def _mark_retry_exhausted_step(state: AgentState) -> dict:
        retries = state["verification_retries"]
        message = (
            "Verification was not achieved after "
            f"{retries} allowed re-research attempt(s)."
        )
        return {
            "verification_report": (
                f"{state['verification_report']}\n"
                f"**Workflow Outcome:** RETRY_EXHAUSTED\n{message}"
            ),
            "terminal_outcome": TerminalOutcome.RETRY_EXHAUSTED,
        }

    @staticmethod
    def _mark_failure_step(state: AgentState) -> dict:
        if state["verification_report"]:
            return {}
        message = state["structured_error"] or "The workflow could not reach a typed terminal state."
        return {"verification_report": f"**Workflow Outcome:** FAILURE\n{message}"}
