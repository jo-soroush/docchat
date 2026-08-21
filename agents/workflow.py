from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
from .research_agent import ResearchAgent
from .verification_agent import VerificationAgent
from .relevance_checker import RelevanceChecker
from langchain.schema import Document
from langchain.retrievers import EnsembleRetriever
from config.settings import Settings, settings
from providers.contracts import ChatProvider
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    question: str
    documents: List[Document]
    draft_answer: str
    verification_report: str
    is_relevant: bool
    retriever: EnsembleRetriever
    verification_retries: int
    terminal_outcome: str

class AgentWorkflow:
    def __init__(self, chat_provider: ChatProvider, config: Settings = settings):
        self.researcher = ResearchAgent(chat_provider)
        self.verifier = VerificationAgent(chat_provider)
        self.relevance_checker = RelevanceChecker(chat_provider)
        self.config = config
        self.compiled_workflow = self.build_workflow()  # Compile once during initialization
        
    def build_workflow(self):
        """Create and compile the multi-agent workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("check_relevance", self._check_relevance_step)
        workflow.add_node("mark_out_of_scope", self._mark_out_of_scope_step)
        workflow.add_node("research", self._research_step)
        workflow.add_node("verify", self._verification_step)
        workflow.add_node("record_retry", self._record_retry_step)
        workflow.add_node("mark_verified", self._mark_verified_step)
        workflow.add_node("mark_retry_exhausted", self._mark_retry_exhausted_step)
        
        # Define edges
        workflow.set_entry_point("check_relevance")
        workflow.add_conditional_edges(
            "check_relevance",
            self._decide_after_relevance_check,
            {
                "relevant": "research",
                "irrelevant": "mark_out_of_scope",
            }
        )
        workflow.add_edge("mark_out_of_scope", END)
        workflow.add_edge("research", "verify")
        workflow.add_conditional_edges(
            "verify",
            self._decide_next_step,
            {
                "re_research": "record_retry",
                "verified": "mark_verified",
                "retry_exhausted": "mark_retry_exhausted",
            }
        )
        workflow.add_edge("record_retry", "research")
        workflow.add_edge("mark_verified", END)
        workflow.add_edge("mark_retry_exhausted", END)
        return workflow.compile()
    
    def _check_relevance_step(self, state: AgentState) -> Dict:
        retriever = state["retriever"]
        classification = self.relevance_checker.check(
            question=state["question"], 
            retriever=retriever, 
            k=20
        )

        if classification == "CAN_ANSWER":
            # We have enough info to proceed
            return {"is_relevant": True}

        elif classification == "PARTIAL":
            # There's partial coverage, but we can still proceed
            return {
                "is_relevant": True
            }

        else:  # classification == "NO_MATCH"
            return {
                "is_relevant": False,
                "draft_answer": "This question isn't related (or there's no data) for your query. Please ask another question relevant to the uploaded document(s)."
            }

    def _mark_out_of_scope_step(self, _: AgentState) -> Dict:
        return {"terminal_outcome": "OUT_OF_SCOPE"}


    def _decide_after_relevance_check(self, state: AgentState) -> str:
        decision = "relevant" if state["is_relevant"] else "irrelevant"
        print(f"[DEBUG] _decide_after_relevance_check -> {decision}")
        return decision
    
    def full_pipeline(self, question: str, retriever: EnsembleRetriever):
        try:
            print(f"[DEBUG] Starting full_pipeline with question='{question}'")
            documents = retriever.invoke(question)
            logger.info(f"Retrieved {len(documents)} relevant documents (from .invoke)")

            initial_state = AgentState(
                question=question,
                documents=documents,
                draft_answer="",
                verification_report="",
                is_relevant=False,
                retriever=retriever,
                verification_retries=0,
                terminal_outcome="FAILURE",
            )
            
            final_state = self.compiled_workflow.invoke(initial_state)
            
            return {
                "draft_answer": final_state["draft_answer"],
                "verification_report": final_state["verification_report"],
                "verification_retries": final_state["verification_retries"],
                "terminal_outcome": final_state["terminal_outcome"],
            }
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise
    
    def _research_step(self, state: AgentState) -> Dict:
        print(f"[DEBUG] Entered _research_step with question='{state['question']}'")
        result = self.researcher.generate(state["question"], state["documents"])
        print("[DEBUG] Researcher returned draft answer.")
        return {"draft_answer": result["draft_answer"]}
    
    def _verification_step(self, state: AgentState) -> Dict:
        print("[DEBUG] Entered _verification_step. Verifying the draft answer...")
        result = self.verifier.check(state["draft_answer"], state["documents"])
        print("[DEBUG] VerificationAgent returned a verification report.")
        return {"verification_report": result["verification_report"]}

    def _record_retry_step(self, state: AgentState) -> Dict:
        return {"verification_retries": state["verification_retries"] + 1}

    def _mark_verified_step(self, _: AgentState) -> Dict:
        return {"terminal_outcome": "VERIFIED"}

    def _mark_retry_exhausted_step(self, state: AgentState) -> Dict:
        retries = state["verification_retries"]
        message = (
            "Verification was not achieved after "
            f"{retries} allowed re-research attempt(s)."
        )
        report = state["verification_report"]
        if report:
            report = f"{report}\n**Workflow Outcome:** RETRY_EXHAUSTED\n{message}"
        else:
            report = f"**Workflow Outcome:** RETRY_EXHAUSTED\n{message}"
        return {
            "verification_report": report,
            "terminal_outcome": "RETRY_EXHAUSTED",
        }
    
    def _decide_next_step(self, state: AgentState) -> str:
        verification_report = state["verification_report"]
        print(f"[DEBUG] _decide_next_step with verification_report='{verification_report}'")
        if not self._verification_requires_research(verification_report):
            logger.info("[DEBUG] Verification successful, ending workflow.")
            return "verified"
        if state["verification_retries"] < self.config.MAX_VERIFICATION_RETRIES:
            logger.info("[DEBUG] Verification indicates bounded re-research.")
            return "re_research"
        logger.info("[DEBUG] Verification retry budget exhausted.")
        return "retry_exhausted"

    @staticmethod
    def _verification_requires_research(verification_report: str) -> bool:
        """Interpret the existing formatted verification report for C03 routing only."""
        return (
            "**Supported:** NO" in verification_report
            or "**Relevant:** NO" in verification_report
        )
