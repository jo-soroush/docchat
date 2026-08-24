"""Focused V1 Hotfix B tests for typed product evidence semantics."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.citations import resolve_claim_sources
from agents.contracts import ClaimSource
from agents.workflow import AgentWorkflow
from config.settings import Settings
from product.operations import ResearchOperation, build_operation_request
from retriever.evidence import ActiveDocumentEvidenceRetriever, EvidenceIntent


class StaticHybridRetriever:
    def __init__(self, response: list[Document]) -> None:
        self.response = response
        self.questions: list[str] = []

    def invoke(self, question: str) -> list[Document]:
        self.questions.append(question)
        return self.response


class RecordingProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        self.calls.append({"prompt": prompt, "schema": schema, "temperature": temperature, "max_tokens": max_tokens})
        return next(self.responses)


def document(
    document_id: str, chunk_id: str, content: str, section: str | None = "Evidence"
) -> Document:
    metadata = {
        "document_id": document_id,
        "chunk_id": chunk_id,
        "source_name": f"{document_id}.pdf",
    }
    if section is not None:
        metadata["section"] = section
    return Document(
        page_content=content,
        metadata=metadata,
    )


def research(answer: str, claims: dict[str, list[str]]) -> str:
    return json.dumps(
        {
            "draft_answer": answer,
            "claim_sources": [
                {"claim": claim, "chunk_ids": chunk_ids}
                for claim, chunk_ids in claims.items()
            ],
        }
    )


def verification(*, supported: bool = True, relevant: bool = True) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": relevant,
            "unsupported_claims": [] if supported else ["unsupported claim"],
            "contradictions": [],
            "correction_feedback": "",
        }
    )


class ProductEvidenceSemanticsTests(TestCase):
    def setUp(self) -> None:
        self.source_a = [
            document("source-a", f"a-{index}", f"Source A evidence {index}")
            for index in range(8)
        ]
        self.source_b = [
            document("source-b", f"b-{index}", f"Source B evidence {index}")
            for index in range(8)
        ]

    def evidence_retriever(self, documents: list[Document], *, max_chunks: int = 4):
        hybrid = StaticHybridRetriever([document("stale", "stale-1", "Stale persisted evidence")])
        return ActiveDocumentEvidenceRetriever(hybrid, documents, max_chunks), hybrid

    def test_ask_and_explain_concept_keep_question_semantics(self) -> None:
        for operation, focus in (
            (ResearchOperation.ASK, "What does source A say?"),
            (ResearchOperation.EXPLAIN_CONCEPT, "hybrid retrieval"),
        ):
            with self.subTest(operation=operation):
                request = build_operation_request(operation.value, focus)
                retriever, hybrid = self.evidence_retriever(self.source_a)
                selection = retriever.collect_evidence(request.evidence_intent, request.question)
                self.assertEqual(request.evidence_intent, EvidenceIntent.QUESTION)
                self.assertEqual(selection.documents[0].metadata["document_id"], "stale")
                self.assertEqual(hybrid.questions, [request.question])

    def test_synthesis_operations_use_active_document_evidence_not_question_top_k(self) -> None:
        for operation in (
            ResearchOperation.SUMMARIZE,
            ResearchOperation.KEY_POINTS,
            ResearchOperation.STUDY_QUESTIONS,
        ):
            with self.subTest(operation=operation):
                request = build_operation_request(operation.value, "")
                retriever, hybrid = self.evidence_retriever(self.source_a)
                selection = retriever.collect_evidence(request.evidence_intent, request.question)
                self.assertEqual(request.evidence_intent, EvidenceIntent.DOCUMENT_SYNTHESIS)
                self.assertTrue(selection.is_sufficient)
                self.assertLessEqual(len(selection.documents), 4)
                self.assertEqual({doc.metadata["document_id"] for doc in selection.documents}, {"source-a"})
                self.assertEqual(hybrid.questions, [])

    def test_synthesis_selection_is_bounded_and_deterministic(self) -> None:
        retriever, _ = self.evidence_retriever(self.source_a, max_chunks=4)
        first = retriever.collect_evidence(EvidenceIntent.DOCUMENT_SYNTHESIS, "Summarize")
        second = retriever.collect_evidence(EvidenceIntent.DOCUMENT_SYNTHESIS, "Summarize")
        first_ids = [doc.metadata["chunk_id"] for doc in first.documents]
        self.assertEqual(first_ids, ["a-0", "a-2", "a-4", "a-7"])
        self.assertEqual(first_ids, [doc.metadata["chunk_id"] for doc in second.documents])
        self.assertLessEqual(len(first.documents), 4)

    def test_section_aware_synthesis_covers_early_and_later_sections(self) -> None:
        large_document = [
            document("source-a", f"chunk-{index}", f"Evidence {index}", f"Section {index}")
            for index in range(24)
        ]
        retriever, hybrid = self.evidence_retriever(large_document, max_chunks=12)

        first = retriever.collect_evidence(EvidenceIntent.DOCUMENT_SYNTHESIS, "Summarize")
        second = retriever.collect_evidence(EvidenceIntent.DOCUMENT_SYNTHESIS, "Summarize")
        first_ids = [item.metadata["chunk_id"] for item in first.documents]

        self.assertEqual(len(first.documents), 12)
        self.assertIn("chunk-6", first_ids)
        self.assertIn("chunk-23", first_ids)
        self.assertEqual(len({item.metadata["section"] for item in first.documents}), 12)
        self.assertEqual(first_ids, [item.metadata["chunk_id"] for item in second.documents])
        self.assertEqual({item.metadata["document_id"] for item in first.documents}, {"source-a"})
        self.assertEqual(hybrid.questions, [])

    def test_section_aware_selection_preserves_multiple_chunk_section_provenance(self) -> None:
        documents = [
            document("source-a", "a-0", "A first", "Alpha"),
            document("source-a", "a-1", "A second", "Alpha"),
            document("source-a", "b-0", "B first", "Beta"),
            document("source-a", "b-1", "B second", "Beta"),
            document("source-a", "c-0", "C first", "Gamma"),
            document("source-a", "c-1", "C second", "Gamma"),
        ]
        retriever, _ = self.evidence_retriever(documents, max_chunks=4)

        selection = retriever.collect_evidence(EvidenceIntent.DOCUMENT_SYNTHESIS, "Summarize")
        citations = resolve_claim_sources(
            [ClaimSource(claim="Alpha evidence", chunk_ids=["a-0"])],
            list(selection.documents),
        )

        self.assertLessEqual(len(selection.documents), 4)
        self.assertEqual({item.metadata["section"] for item in selection.documents}, {"Alpha", "Beta", "Gamma"})
        self.assertTrue(citations[0].available)
        self.assertEqual(citations[0].source_name, "source-a.pdf")
        self.assertEqual(citations[0].section, "Alpha")

    def test_section_poor_synthesis_uses_deterministic_positional_fallback(self) -> None:
        section_poor = [
            document("source-a", f"chunk-{index}", f"Evidence {index}", None)
            for index in range(8)
        ]
        retriever, _ = self.evidence_retriever(section_poor, max_chunks=4)

        selection = retriever.collect_evidence(EvidenceIntent.DOCUMENT_SYNTHESIS, "Summarize")

        self.assertEqual(
            [item.metadata["chunk_id"] for item in selection.documents],
            ["chunk-0", "chunk-2", "chunk-4", "chunk-7"],
        )

    def test_synthesis_uses_existing_workflow_provider_and_verification_boundaries(self) -> None:
        retriever, hybrid = self.evidence_retriever(self.source_a)
        provider = RecordingProvider(
            [
                research("A grounded summary.", {"summary": ["a-0"]}),
                verification(),
            ]
        )
        request = build_operation_request(ResearchOperation.SUMMARIZE.value, "")

        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            request.question,
            retriever,
            evidence_intent=request.evidence_intent,
            operation=request.operation.value,
        )

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(hybrid.questions, [])
        self.assertIn(f"Question: {request.question}", provider.calls[1]["prompt"])

    def test_compare_requires_two_active_documents(self) -> None:
        retriever, _ = self.evidence_retriever(self.source_a)
        workflow = AgentWorkflow(RecordingProvider([]), Settings(_env_file=None))

        result = workflow.full_pipeline(
            "Compare the uploaded document sources.",
            retriever,
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
            operation=ResearchOperation.COMPARE_SOURCES.value,
        )

        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertEqual(result["draft_answer"], "Compare Sources requires at least two active uploaded documents.")
        self.assertEqual(result["citations"], [])

    def test_compare_collects_balanced_attributable_evidence_and_preserves_citations(self) -> None:
        retriever, _ = self.evidence_retriever([*self.source_a, *self.source_b], max_chunks=4)
        selection = retriever.collect_evidence(
            EvidenceIntent.MULTI_DOCUMENT_COMPARISON, "Compare the uploaded document sources."
        )
        self.assertEqual(len(selection.documents), 4)
        self.assertEqual(
            [document.metadata["document_id"] for document in selection.documents],
            ["source-a", "source-a", "source-b", "source-b"],
        )

        provider = RecordingProvider(
            [
                research(
                    "Source A and Source B both provide evidence.",
                    {"Source A evidence": ["a-0"], "Source B evidence": ["b-0"]},
                ),
                verification(),
            ]
        )
        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            "Compare the uploaded document sources.",
            retriever,
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
            operation=ResearchOperation.COMPARE_SOURCES.value,
        )
        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual({citation["document_id"] for citation in result["citations"]}, {"source-a", "source-b"})
        self.assertIn("Question: Compare the uploaded document sources.", provider.calls[1]["prompt"])
