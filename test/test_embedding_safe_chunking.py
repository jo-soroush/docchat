"""Focused V1 maintenance tests for embedding-safe document chunk representation."""

import hashlib
import pickle
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from langchain.schema import Document

from agents.citations import resolve_claim_sources
from agents.contracts import ClaimSource
from config.settings import Settings
from document_processor.file_handler import DocumentProcessor
from retriever.builder import RetrieverBuilder


class LengthBoundEmbeddingProvider:
    """Deterministic embedding fake that rejects an unbounded input explicitly."""

    def __init__(self, maximum_length: int) -> None:
        self.maximum_length = maximum_length

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if any(len(text) > self.maximum_length for text in texts):
            raise AssertionError("Oversized chunk reached the embedding boundary.")
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), float(sum(map(ord, text)) % 101), 1.0]


class EmbeddingSafeChunkingTests(TestCase):
    def _processor(self, directory: str, maximum: int = 256) -> DocumentProcessor:
        return DocumentProcessor(
            Settings(
                _env_file=None,
                CACHE_DIR=str(Path(directory) / "cache"),
                DOCUMENT_CHUNK_MAX_CHARACTERS=maximum,
            )
        )

    @staticmethod
    def _oversized_document() -> Document:
        return Document(
            page_content=("Grounded evidence sentence. " * 40).strip(),
            metadata={
                "Header 1": "Theory",
                "Header 2": "Embedding Safety",
                "source_name": "guide.pdf",
                "document_id": "source-id",
                "page": 3,
            },
        )

    def test_normal_sized_chunk_is_unchanged(self) -> None:
        with TemporaryDirectory() as directory:
            processor = self._processor(directory)
            normal = Document(page_content="Short evidence.", metadata={"Header 1": "Overview"})

            bounded, migrated = processor._bound_chunk_size([normal])

            self.assertFalse(migrated)
            self.assertEqual(bounded, [normal])
            self.assertIs(bounded[0], normal)

    def test_chunk_size_configuration_has_a_safe_default_and_bounds(self) -> None:
        self.assertEqual(Settings(_env_file=None).DOCUMENT_CHUNK_MAX_CHARACTERS, 4000)
        for value in (255, 16001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Settings(_env_file=None, DOCUMENT_CHUNK_MAX_CHARACTERS=value)

    def test_oversized_chunk_is_bounded_with_metadata_and_stable_unique_ids(self) -> None:
        with TemporaryDirectory() as directory:
            processor = self._processor(directory)
            bounded, migrated = processor._bound_chunk_size([self._oversized_document()])
            processor._attach_provenance(bounded, "source-id", "guide.pdf")

            self.assertTrue(migrated)
            self.assertGreater(len(bounded), 1)
            self.assertTrue(
                all(len(chunk.page_content) <= processor.config.DOCUMENT_CHUNK_MAX_CHARACTERS for chunk in bounded)
            )
            self.assertTrue(
                all(
                    chunk.metadata["document_id"] == "source-id"
                    and chunk.metadata["source_name"] == "guide.pdf"
                    and chunk.metadata["section"] == "Embedding Safety"
                    and chunk.metadata["page"] == 3
                    for chunk in bounded
                )
            )
            first_ids = [chunk.metadata["chunk_id"] for chunk in bounded]
            second, _ = processor._bound_chunk_size([self._oversized_document()])
            processor._attach_provenance(second, "source-id", "guide.pdf")
            self.assertEqual(first_ids, [chunk.metadata["chunk_id"] for chunk in second])
            self.assertEqual(len(first_ids), len(set(first_ids)))

    def test_legacy_cached_oversized_chunks_migrate_without_deleting_the_cache(self) -> None:
        with TemporaryDirectory() as directory:
            processor = self._processor(directory)
            source = Path(directory) / "legacy.md"
            source.write_text("legacy source", encoding="utf-8")
            file_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            cache_path = processor.cache_dir / f"{file_hash}.pkl"
            with cache_path.open("wb") as cache:
                pickle.dump({"timestamp": 1, "chunks": [self._oversized_document()]}, cache)
            # Keep the legacy cache fresh so the test specifically exercises migration.
            cache_path.touch()

            with patch.object(processor, "_process_file") as parse:
                first = processor.process([SimpleNamespace(name=str(source))])
                second = processor.process([SimpleNamespace(name=str(source))])

            self.assertFalse(parse.called)
            self.assertTrue(cache_path.exists())
            with cache_path.open("rb") as cache:
                cached_chunks = pickle.load(cache)["chunks"]
            self.assertTrue(
                all(len(chunk.page_content) <= processor.config.DOCUMENT_CHUNK_MAX_CHARACTERS for chunk in cached_chunks)
            )
            self.assertEqual(
                [chunk.metadata["chunk_id"] for chunk in first],
                [chunk.metadata["chunk_id"] for chunk in second],
            )

    def test_two_document_hybrid_build_embeds_only_bounded_chunks_and_preserves_sources(self) -> None:
        with TemporaryDirectory() as directory:
            processor = self._processor(directory)
            first, _ = processor._bound_chunk_size([self._oversized_document()])
            second = [
                Document(
                    page_content="Second source evidence.",
                    metadata={"Header 1": "Comparison", "source_name": "second.pdf"},
                )
            ]
            processor._attach_provenance(first, "source-a", "guide.pdf")
            processor._attach_provenance(second, "source-b", "second.pdf")
            documents = first + second
            config = Settings(
                _env_file=None,
                CHROMA_DB_PATH=str(Path(directory) / "chroma"),
                CHROMA_COLLECTION_NAME="bounded-two-source",
                VECTOR_SEARCH_K=3,
                DOCUMENT_CHUNK_MAX_CHARACTERS=256,
            )
            modes = RetrieverBuilder(LengthBoundEmbeddingProvider(256), config).build_evaluation_modes(
                documents, k=3
            )
            vector_documents = modes.vector.invoke("evidence")
            citations = resolve_claim_sources(
                [
                    ClaimSource(
                        claim="First-source evidence.",
                        chunk_ids=[first[0].metadata["chunk_id"]],
                    ),
                    ClaimSource(
                        claim="Second-source evidence.",
                        chunk_ids=[second[0].metadata["chunk_id"]],
                    ),
                ],
                documents,
            )

            self.assertEqual(modes.vector.vectorstore._collection.count(), len(documents))
            self.assertEqual({item.metadata["document_id"] for item in vector_documents}, {"source-a", "source-b"})
            self.assertEqual({citation.source_name for citation in citations}, {"guide.pdf", "second.pdf"})
            self.assertTrue(all(citation.available for citation in citations))
