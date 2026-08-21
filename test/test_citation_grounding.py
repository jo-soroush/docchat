"""Focused V1-C05 tests for local provenance and inspectable citations."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from langchain.schema import Document

from agents.citations import format_citation_report, resolve_claim_sources
from agents.contracts import ClaimSource
from agents.workflow import AgentWorkflow
from config.settings import Settings
from document_processor.file_handler import DocumentProcessor
from retriever.builder import RetrieverBuilder


class FakeChatProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        return next(self.responses)


class FakeRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


class FakeEmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]


def relevance() -> str:
    return json.dumps({"decision": "CAN_ANSWER", "explanation": "grounded"})


def research(claim_sources: list[dict] | None = None) -> str:
    result = {"draft_answer": "DocChat uses hybrid retrieval."}
    if claim_sources is not None:
        result["claim_sources"] = claim_sources
    return json.dumps(result)


def verification() -> str:
    return json.dumps(
        {
            "supported": True,
            "relevant": True,
            "unsupported_claims": [],
            "contradictions": [],
            "correction_feedback": "grounded",
        }
    )


class CitationGroundingTests(TestCase):
    def test_provenance_is_stable_across_fresh_processing_and_cached_reload(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "report.md"
            source_path.write_text("source content", encoding="utf-8")
            processor = DocumentProcessor()
            processor.cache_dir = Path(directory) / "cache"
            processor.cache_dir.mkdir()
            chunks = [
                Document(page_content="First chunk", metadata={"Header 1": "Introduction"}),
                Document(page_content="Second chunk", metadata={"Header 2": "Details"}),
            ]
            file = SimpleNamespace(name=str(source_path))

            with patch.object(processor, "_process_file", return_value=chunks) as process_file:
                fresh = processor.process([file])
                cached = processor.process([file])

            self.assertEqual(process_file.call_count, 1)
            self.assertEqual(
                [chunk.metadata["chunk_id"] for chunk in fresh],
                [chunk.metadata["chunk_id"] for chunk in cached],
            )
            self.assertEqual(fresh[0].metadata["document_id"], cached[0].metadata["document_id"])
            self.assertEqual(fresh[0].metadata["source_name"], "report.md")
            self.assertEqual(fresh[0].metadata["section"], "Introduction")
            self.assertEqual(fresh[1].metadata["section"], "Details")

    def test_valid_claim_mapping_resolves_to_retrieved_source_metadata(self) -> None:
        document = Document(
            page_content="DocChat combines BM25 and vector retrieval.",
            metadata={
                "chunk_id": "chunk-1",
                "document_id": "document-1",
                "source_name": "guide.md",
                "section": "Retrieval",
                "page": 4,
            },
        )
        workflow = AgentWorkflow(
            FakeChatProvider(
                [
                    relevance(),
                    research([{"claim": "DocChat uses hybrid retrieval.", "chunk_ids": ["chunk-1"]}]),
                    verification(),
                ]
            ),
            Settings(_env_file=None),
        )

        final = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever([document]))

        self.assertEqual(final["terminal_outcome"], "VERIFIED")
        self.assertEqual(final["citations"][0]["chunk_id"], "chunk-1")
        self.assertEqual(final["citations"][0]["source_name"], "guide.md")
        self.assertIn("section: Retrieval", final["citation_report"])
        self.assertIn("page: 4", final["citation_report"])

    def test_hybrid_retrieval_preserves_chunk_provenance_metadata(self) -> None:
        document = Document(
            page_content="DocChat uses hybrid retrieval.",
            metadata={
                "chunk_id": "chunk-1",
                "document_id": "document-1",
                "source_name": "guide.md",
                "section": "Retrieval",
            },
        )
        with TemporaryDirectory() as directory:
            config = Settings(_env_file=None, CHROMA_DB_PATH=directory, VECTOR_SEARCH_K=1)
            retriever = RetrieverBuilder(FakeEmbeddingProvider(), config).build_hybrid_retriever(
                [document]
            )
            retrieved = retriever.invoke("How does DocChat retrieve?")

        self.assertTrue(retrieved)
        self.assertEqual(retrieved[0].metadata["chunk_id"], "chunk-1")
        self.assertEqual(retrieved[0].metadata["source_name"], "guide.md")

    def test_unknown_model_chunk_id_is_explicitly_unavailable_without_routing_change(self) -> None:
        document = Document(page_content="Known evidence.", metadata={"chunk_id": "known"})
        workflow = AgentWorkflow(
            FakeChatProvider(
                [
                    relevance(),
                    research([{"claim": "A claim", "chunk_ids": ["not-retrieved"]}]),
                    verification(),
                ]
            ),
            Settings(_env_file=None),
        )

        final = workflow.full_pipeline("Question", FakeRetriever([document]))

        self.assertEqual(final["terminal_outcome"], "VERIFIED")
        self.assertFalse(final["citations"][0]["available"])
        self.assertIn("Citation unavailable (not-retrieved)", final["citation_report"])

    def test_missing_claim_mapping_has_graceful_user_fallback(self) -> None:
        document = Document(page_content="Known evidence.", metadata={"chunk_id": "known"})
        workflow = AgentWorkflow(
            FakeChatProvider([relevance(), research(), verification()]), Settings(_env_file=None)
        )

        final = workflow.full_pipeline("Question", FakeRetriever([document]))

        self.assertEqual(final["terminal_outcome"], "VERIFIED")
        self.assertEqual(final["citations"], [])
        self.assertIn("Citations unavailable", final["citation_report"])

    def test_empty_or_unknown_source_mapping_formats_without_source_invention(self) -> None:
        citations = resolve_claim_sources(
            [
                ClaimSource(claim="No ID", chunk_ids=[]),
                ClaimSource(claim="Unknown ID", chunk_ids=["missing"]),
            ],
            [],
        )

        report = format_citation_report(citations)

        self.assertEqual(len(citations), 2)
        self.assertTrue(all(not citation.available for citation in citations))
        self.assertIn("Citation unavailable (no chunk ID)", report)
        self.assertIn("Citation unavailable (missing)", report)
