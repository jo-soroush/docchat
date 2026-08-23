"""Focused Hotfix A tests for Chroma identity and active-document isolation."""

from tempfile import TemporaryDirectory
from unittest import TestCase

from langchain.schema import Document

from agents.citations import resolve_claim_sources
from agents.contracts import ClaimSource
from config.settings import Settings
from retriever.builder import RetrievalError, RetrieverBuilder


class DeterministicEmbeddingProvider:
    """Small local fake that keeps vector-store tests deterministic."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), float(sum(map(ord, text)) % 101), 1.0]


def document(document_id: str, chunk_id: str, content: str, source_name: str) -> Document:
    return Document(
        page_content=content,
        metadata={
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source_name": source_name,
            "section": "Evidence",
        },
    )


class ChromaScopingTests(TestCase):
    def setUp(self) -> None:
        self.document_a = document("document-a", "chunk-a", "alpha evidence", "a.txt")
        self.document_b = document("document-b", "chunk-b", "beta evidence", "b.txt")

    def _builder(self, directory: str) -> RetrieverBuilder:
        return RetrieverBuilder(
            DeterministicEmbeddingProvider(),
            Settings(
                _env_file=None,
                CHROMA_DB_PATH=directory,
                CHROMA_COLLECTION_NAME="hotfix-a-test",
                VECTOR_SEARCH_K=3,
            ),
        )

    def test_repeated_ingestion_upserts_existing_chunk_ids_without_duplicates(self) -> None:
        with TemporaryDirectory() as directory:
            builder = self._builder(directory)
            first = builder.build_evaluation_modes([self.document_a, self.document_b], k=3)
            second = builder.build_evaluation_modes([self.document_a, self.document_b], k=3)

            collection = second.vector.vectorstore._collection
            self.assertEqual(collection.name, "hotfix-a-test")
            self.assertEqual(collection.count(), 2)
            self.assertEqual(set(collection.get()["ids"]), {"chunk-a", "chunk-b"})
            self.assertEqual(first.vector.vectorstore._collection.count(), 2)

    def test_vector_and_hybrid_exclude_previously_persisted_inactive_documents(self) -> None:
        with TemporaryDirectory() as directory:
            builder = self._builder(directory)
            builder.build_evaluation_modes([self.document_a, self.document_b], k=3)
            active_a = builder.build_evaluation_modes([self.document_a], k=3)

            vector_documents = active_a.vector.invoke("beta evidence")
            hybrid_documents = active_a.hybrid.invoke("beta evidence")

            self.assertTrue(vector_documents)
            self.assertTrue(hybrid_documents)
            self.assertEqual({item.metadata["document_id"] for item in vector_documents}, {"document-a"})
            self.assertEqual({item.metadata["document_id"] for item in hybrid_documents}, {"document-a"})

    def test_multi_document_active_scope_keeps_both_sources_eligible(self) -> None:
        with TemporaryDirectory() as directory:
            modes = self._builder(directory).build_evaluation_modes(
                [self.document_a, self.document_b], k=3
            )

            vector_documents = modes.vector.invoke("evidence")
            hybrid_documents = modes.hybrid.invoke("evidence")

            self.assertEqual(
                {item.metadata["document_id"] for item in vector_documents},
                {"document-a", "document-b"},
            )
            self.assertEqual(
                {item.metadata["document_id"] for item in hybrid_documents},
                {"document-a", "document-b"},
            )

    def test_bm25_stays_scoped_to_current_documents(self) -> None:
        with TemporaryDirectory() as directory:
            builder = self._builder(directory)
            builder.build_evaluation_modes([self.document_a, self.document_b], k=3)
            active_a = builder.build_evaluation_modes([self.document_a], k=3)

            documents = active_a.bm25.invoke("beta evidence")

            self.assertEqual({item.metadata["document_id"] for item in documents}, {"document-a"})

    def test_scoped_retrieval_preserves_citation_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            modes = self._builder(directory).build_evaluation_modes([self.document_a], k=3)
            retrieved = modes.hybrid.invoke("alpha evidence")

            citations = resolve_claim_sources(
                [ClaimSource(claim="Alpha is present.", chunk_ids=["chunk-a"])], retrieved
            )

            self.assertEqual(len(citations), 1)
            self.assertTrue(citations[0].available)
            self.assertEqual(citations[0].document_id, "document-a")
            self.assertEqual(citations[0].source_name, "a.txt")

    def test_missing_c05_identity_fails_at_the_retrieval_boundary(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RetrievalError, "could not be initialized"):
                self._builder(directory).build_evaluation_modes(
                    [Document(page_content="legacy identity-free content")], k=3
                )
