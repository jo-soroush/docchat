"""Focused V1-C09 tests for controlled failure ownership and safe traces."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from langchain.schema import Document

from agents.workflow import AgentWorkflow
from config.settings import Settings
from document_processor.file_handler import DocumentProcessingError, DocumentProcessor
from providers.contracts import ProviderError
from retriever.builder import RetrievalError, RetrieverBuilder


class FailingProvider:
    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        raise ProviderError("raw provider detail")

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        del schema
        return self.generate(prompt, temperature=temperature, max_tokens=max_tokens)


class FailingRetriever:
    def invoke(self, _: str):
        raise ProviderError("raw retrieval detail")


class RawFailingRetriever:
    def invoke(self, _: str):
        raise RuntimeError("raw third-party retrieval detail")


class FailingEmbedding:
    def embed_documents(self, texts):
        raise ProviderError("raw embedding detail")

    def embed_query(self, text):
        raise ProviderError("raw embedding detail")


class RobustFailureTests(TestCase):
    def test_zero_documents_fail_before_retrieval(self) -> None:
        processor = DocumentProcessor()
        with self.assertRaisesRegex(DocumentProcessingError, "No documents were provided"):
            processor.process([])

    def test_provider_failure_is_terminal_and_safe_in_trace(self) -> None:
        result = AgentWorkflow(FailingProvider(), Settings(_env_file=None)).full_pipeline(
            "private question", StaticRetriever()
        )
        trace = str(result["run_trace"])
        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertIn("The relevance provider was unavailable.", trace)
        self.assertNotIn("raw provider detail", trace)
        self.assertNotIn("private question", trace)

    def test_retrieval_failure_returns_safe_terminal_trace_without_answer_or_citations(self) -> None:
        result = AgentWorkflow(FailingProvider(), Settings(_env_file=None)).full_pipeline(
            "private question", FailingRetriever()
        )
        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertEqual(result["draft_answer"], "Document retrieval was unavailable.")
        self.assertEqual(result["citations"], [])
        self.assertNotIn("raw retrieval detail", str(result["run_trace"]))

    def test_untyped_retriever_failure_is_safe_and_traceable(self) -> None:
        result = AgentWorkflow(FailingProvider(), Settings(_env_file=None)).full_pipeline(
            "private question", RawFailingRetriever()
        )
        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertEqual(result["citations"], [])
        self.assertNotIn("raw third-party retrieval detail", str(result["run_trace"]))

    def test_retriever_build_failure_is_wrapped_without_raw_provider_detail(self) -> None:
        with TemporaryDirectory() as directory:
            builder = RetrieverBuilder(
                FailingEmbedding(), Settings(_env_file=None, CHROMA_DB_PATH=directory)
            )
            with self.assertRaisesRegex(RetrievalError, "Document retrieval could not be initialized") as raised:
                builder.build_hybrid_retriever([Document(page_content="content")])
        self.assertNotIn("raw embedding detail", str(raised.exception))

    def test_corrupt_cache_rebuilds_from_source_and_all_unusable_files_fail_explicitly(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "doc.md"
            path.write_text("source", encoding="utf-8")
            processor = DocumentProcessor()
            processor.cache_dir = Path(directory) / "cache"
            processor.cache_dir.mkdir()
            file = SimpleNamespace(name=str(path))
            file_hash = processor._generate_hash(path.read_bytes())
            (processor.cache_dir / f"{file_hash}.pkl").write_bytes(b"corrupt")
            chunks = [Document(page_content="usable")]
            with patch.object(processor, "_process_file", return_value=chunks) as process_file:
                result = processor.process([file])
            self.assertEqual(process_file.call_count, 1)
            self.assertEqual(result[0].page_content, "usable")
            (processor.cache_dir / f"{file_hash}.pkl").unlink()
            with patch.object(processor, "_process_file", return_value=[]):
                with self.assertRaises(DocumentProcessingError):
                    processor.process([file])

    def test_partial_upload_failure_preserves_usable_document(self) -> None:
        with TemporaryDirectory() as directory:
            usable_path = Path(directory) / "usable.md"
            usable_path.write_text("source", encoding="utf-8")
            processor = DocumentProcessor()
            processor.cache_dir = Path(directory) / "cache"
            processor.cache_dir.mkdir()
            missing = SimpleNamespace(name=str(Path(directory) / "missing.md"))
            usable = SimpleNamespace(name=str(usable_path))
            with patch.object(
                processor,
                "_process_file",
                return_value=[Document(page_content="usable")],
            ):
                result = processor.process([missing, usable])
        self.assertEqual([chunk.page_content for chunk in result], ["usable"])

    def test_parser_failure_becomes_explicit_no_usable_content_outcome(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "broken.md"
            path.write_text("source", encoding="utf-8")
            processor = DocumentProcessor()
            processor.cache_dir = Path(directory) / "cache"
            processor.cache_dir.mkdir()
            file = SimpleNamespace(name=str(path))
            with patch(
                "document_processor.file_handler.DocumentConverter",
                side_effect=RuntimeError("raw parser detail"),
            ):
                with self.assertRaisesRegex(
                    DocumentProcessingError,
                    "No usable document content could be extracted",
                ) as raised:
                    processor.process([file])
        self.assertNotIn("raw parser detail", str(raised.exception))


class StaticRetriever:
    def invoke(self, _: str):
        return [Document(page_content="evidence", metadata={"chunk_id": "safe"})]
