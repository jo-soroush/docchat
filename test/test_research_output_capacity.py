"""Focused Hotfix B tests for bounded ResearchResult generation capacity."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.research_agent import ResearchAgent
from agents.workflow import AgentWorkflow
from config.settings import Settings
from product.operations import ResearchOperation, build_operation_request
from providers.contracts import ProviderError
from retriever.evidence import ActiveDocumentEvidenceRetriever, EvidenceIntent


def document(document_id: str, chunk_id: str, content: str) -> Document:
    return Document(
        page_content=content,
        metadata={
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source_name": f"{document_id}.pdf",
            "section": "Evidence",
        },
    )


class NoHybridRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.calls: list[str] = []

    def invoke(self, question: str) -> list[Document]:
        self.calls.append(question)
        return self.documents


class RecordingProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        self.calls.append({"prompt": prompt, "schema": schema, "max_tokens": max_tokens})
        return next(self.responses)


class ResearchFailingProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        self.calls.append({"prompt": prompt, "schema": schema, "max_tokens": max_tokens})
        raise ProviderError("Ollama structured response exceeded its generation limit.")


def research_json() -> str:
    return json.dumps(
        {
            "draft_answer": "A grounded summary.",
            "claim_sources": [{"claim": "A grounded summary.", "chunk_ids": ["chunk-a"]}],
        }
    )


def verification_json() -> str:
    return json.dumps(
        {
            "supported": True,
            "relevant": True,
            "unsupported_claims": [],
            "contradictions": [],
            "correction_feedback": "",
        }
    )


class ResearchOutputCapacityTests(TestCase):
    def setUp(self) -> None:
        self.documents = [document("active-document", "chunk-a", "Active evidence.")]

    def test_research_agent_uses_a_bounded_1500_token_structured_request(self) -> None:
        provider = RecordingProvider([research_json()])

        result = ResearchAgent(provider).generate("Summarize the document.", self.documents)

        self.assertEqual(result.draft_answer, "A grounded summary.")
        self.assertEqual(provider.calls[0]["max_tokens"], 1500)

    def test_research_provider_failure_is_safe_and_skips_citations_and_verification(self) -> None:
        hybrid = NoHybridRetriever(self.documents)
        retriever = ActiveDocumentEvidenceRetriever(hybrid, self.documents, max_chunks=12)
        provider = ResearchFailingProvider()

        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            "Summarize the uploaded document(s).",
            retriever,
            evidence_intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
            operation=ResearchOperation.SUMMARIZE.value,
        )

        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertEqual(result["draft_answer"], "The research provider was unavailable.")
        self.assertEqual(result["citations"], [])
        self.assertIsNone(result["verification_result"])
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(hybrid.calls, [])
        self.assertNotIn("exceeded its generation limit", str(result["run_trace"]))

    def test_valid_research_result_resolves_active_citation_then_reaches_verification(self) -> None:
        hybrid = NoHybridRetriever(self.documents)
        retriever = ActiveDocumentEvidenceRetriever(hybrid, self.documents, max_chunks=12)
        provider = RecordingProvider([research_json(), verification_json()])

        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            "Summarize the uploaded document(s).",
            retriever,
            evidence_intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
            operation=ResearchOperation.SUMMARIZE.value,
        )

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(result["citations"][0]["document_id"], "active-document")
        self.assertTrue(result["citations"][0]["available"])
        self.assertEqual(result["verification_result"]["supported"], True)
        self.assertEqual(result["verification_result"]["relevant"], True)
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(hybrid.calls, [])

    def test_question_intent_still_uses_hybrid_retrieval(self) -> None:
        hybrid = NoHybridRetriever(self.documents)
        retriever = ActiveDocumentEvidenceRetriever(hybrid, self.documents, max_chunks=12)
        request = build_operation_request(ResearchOperation.ASK.value, "What is active evidence?")

        selection = retriever.collect_evidence(request.evidence_intent, request.question)

        self.assertEqual(request.evidence_intent, EvidenceIntent.QUESTION)
        self.assertEqual(selection.documents, tuple(self.documents))
        self.assertEqual(hybrid.calls, [request.question])
