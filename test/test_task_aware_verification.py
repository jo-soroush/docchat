"""Focused Hotfix B tests for typed task-aware verification semantics."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.verification_agent import VerificationAgent
from agents.workflow import AgentWorkflow
from config.settings import Settings
from retriever.evidence import ActiveDocumentEvidenceRetriever, EvidenceIntent


class RecordingProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        self.calls.append({"prompt": prompt, "schema": schema, "max_tokens": max_tokens})
        return next(self.responses)


class StaticHybridRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def document(document_id: str, chunk_id: str, content: str) -> Document:
    return Document(
        page_content=content,
        metadata={"document_id": document_id, "chunk_id": chunk_id, "source_name": f"{document_id}.pdf"},
    )


def verification(*, supported: bool, relevant: bool, unsupported: list[str] | None = None) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": relevant,
            "unsupported_claims": unsupported or [],
            "contradictions": [],
            "correction_feedback": "" if supported else "Remove unsupported claims.",
        }
    )


def research() -> str:
    return json.dumps(
        {
            "draft_answer": "A grounded synthesis.",
            "claim_sources": [{"claim": "A grounded synthesis.", "chunk_ids": ["chunk-a"]}],
        }
    )


class TaskAwareVerificationTests(TestCase):
    def setUp(self) -> None:
        self.one_source = [document("source-a", "chunk-a", "Source A evidence.")]
        self.two_sources = [
            document("source-a", "chunk-a", "Source A evidence."),
            document("source-b", "chunk-b", "Source B evidence."),
        ]

    def test_question_semantics_remain_the_default(self) -> None:
        provider = RecordingProvider([verification(supported=True, relevant=True)])

        result = VerificationAgent(provider).check("What is source A?", "Source A evidence.", self.one_source)

        self.assertTrue(result.supported)
        self.assertIn("Verification task intent: QUESTION", provider.calls[0]["prompt"])
        self.assertIn("directly responds to the exact user question", provider.calls[0]["prompt"])

    def test_document_synthesis_can_verify_supported_non_exhaustive_answer(self) -> None:
        provider = RecordingProvider([verification(supported=True, relevant=True)])

        result = VerificationAgent(provider).check(
            "Summarize the uploaded document(s).",
            "A focused grounded synthesis.",
            self.one_source,
            intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
        )

        self.assertFalse(result.requires_research)
        prompt = provider.calls[0]["prompt"]
        self.assertIn("Verification task intent: DOCUMENT_SYNTHESIS", prompt)
        self.assertIn("Do not require\nexhaustive coverage", prompt)
        self.assertIn("Do not treat the\nsynthesis instruction as a factual question", prompt)

    def test_document_synthesis_still_rejects_unsupported_external_claims(self) -> None:
        provider = RecordingProvider([verification(supported=False, relevant=True, unsupported=["external claim"])])

        result = VerificationAgent(provider).check(
            "Summarize the uploaded document(s).",
            "An external claim.",
            self.one_source,
            intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
        )

        self.assertTrue(result.requires_research)
        self.assertIn("external\nknowledge", provider.calls[0]["prompt"])

    def test_multi_document_comparison_receives_both_source_semantics(self) -> None:
        provider = RecordingProvider([verification(supported=True, relevant=True)])

        VerificationAgent(provider).check(
            "Compare the uploaded document sources.",
            "The sources differ.",
            self.two_sources,
            intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        prompt = provider.calls[0]["prompt"]
        self.assertIn("Verification task intent: MULTI_DOCUMENT_COMPARISON", prompt)
        self.assertIn("one source\nto silently stand in for another", prompt)

    def test_workflow_passes_document_synthesis_intent_to_verification(self) -> None:
        provider = RecordingProvider([research(), verification(supported=True, relevant=True)])
        retriever = ActiveDocumentEvidenceRetriever(
            StaticHybridRetriever(self.one_source), self.one_source, max_chunks=12
        )

        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            "Summarize the uploaded document(s).",
            retriever,
            evidence_intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
            operation="summarize",
        )

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertIn("Verification task intent: DOCUMENT_SYNTHESIS", provider.calls[1]["prompt"])

    def test_malformed_verification_output_remains_safe_failure(self) -> None:
        provider = RecordingProvider([research(), '{"supported": true'])
        retriever = ActiveDocumentEvidenceRetriever(
            StaticHybridRetriever(self.one_source), self.one_source, max_chunks=12
        )

        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            "Summarize the uploaded document(s).",
            retriever,
            evidence_intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
        )

        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertEqual(result["verification_result"], None)
