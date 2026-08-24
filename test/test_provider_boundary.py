"""Focused V1-C02 tests for the vendor-neutral provider boundary."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from langchain.schema import Document

from agents.contracts import RelevanceResult, ResearchResult, VerificationResult
from agents.workflow import AgentWorkflow
from config.settings import Settings
from providers.factory import build_runtime_providers
from providers.ollama import (
    OllamaChatProvider,
    OllamaEmbeddingProvider,
    OllamaProviderError,
)
from retriever.builder import RetrieverBuilder


class FakeChatProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        self.calls.append(
            {"prompt": prompt, "temperature": temperature, "max_tokens": max_tokens}
        )
        return next(self.responses)

    def generate_structured(
        self, prompt: str, *, schema: dict, temperature: float, max_tokens: int
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return next(self.responses)


class FakeEmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), float(sum(map(ord, text)) % 97), 1.0]


class FakeRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


class ProviderBoundaryTests(TestCase):
    def test_gradio_server_port_defaults_to_7860(self) -> None:
        self.assertEqual(Settings(_env_file=None).GRADIO_SERVER_PORT, 7860)

    def test_gradio_server_port_accepts_environment_override(self) -> None:
        previous_value = os.environ.get("GRADIO_SERVER_PORT")
        try:
            os.environ["GRADIO_SERVER_PORT"] = "8899"
            self.assertEqual(Settings(_env_file=None).GRADIO_SERVER_PORT, 8899)
        finally:
            if previous_value is None:
                os.environ.pop("GRADIO_SERVER_PORT", None)
            else:
                os.environ["GRADIO_SERVER_PORT"] = previous_value

    def test_gradio_server_port_rejects_out_of_range_value(self) -> None:
        with self.assertRaises(ValueError):
            Settings(_env_file=None, GRADIO_SERVER_PORT=70000)

    def test_ollama_context_window_defaults_to_8192_and_accepts_environment_override(self) -> None:
        self.assertEqual(Settings(_env_file=None).OLLAMA_CONTEXT_WINDOW, 8192)
        previous_value = os.environ.get("OLLAMA_CONTEXT_WINDOW")
        try:
            os.environ["OLLAMA_CONTEXT_WINDOW"] = "16384"
            self.assertEqual(Settings(_env_file=None).OLLAMA_CONTEXT_WINDOW, 16384)
        finally:
            if previous_value is None:
                os.environ.pop("OLLAMA_CONTEXT_WINDOW", None)
            else:
                os.environ["OLLAMA_CONTEXT_WINDOW"] = previous_value

    def test_ollama_context_window_rejects_invalid_values(self) -> None:
        for value in (1023, 65537):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Settings(_env_file=None, OLLAMA_CONTEXT_WINDOW=value)

    def test_ollama_embedding_batch_size_defaults_and_rejects_invalid_values(self) -> None:
        self.assertEqual(Settings(_env_file=None).OLLAMA_EMBEDDING_BATCH_SIZE, 32)
        for value in (0, 257):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Settings(_env_file=None, OLLAMA_EMBEDDING_BATCH_SIZE=value)

    def test_configuration_builds_local_provider_bundle_without_credentials(self) -> None:
        config = Settings(
            _env_file=None,
            OLLAMA_BASE_URL="http://ollama.test:11434",
            OLLAMA_CHAT_MODEL="chat-test",
            OLLAMA_EMBEDDING_MODEL="embed-test",
            OLLAMA_EMBEDDING_BATCH_SIZE=16,
            OLLAMA_CONTEXT_WINDOW=16384,
        )

        bundle = build_runtime_providers(config)

        self.assertEqual(bundle.chat._model.model, "chat-test")
        self.assertEqual(bundle.chat._model.base_url, "http://ollama.test:11434")
        self.assertEqual(bundle.chat._context_window, 16384)
        self.assertEqual(bundle.embeddings._embeddings.model, "embed-test")
        self.assertEqual(bundle.embeddings._batch_size, 16)

    @patch("providers.ollama.ChatOllama")
    def test_ollama_chat_adapter_returns_text_and_passes_generation_options(self, chat_class: Mock) -> None:
        model = chat_class.return_value
        model.bind.return_value.invoke.return_value = SimpleNamespace(content=" local answer ")

        provider = OllamaChatProvider(
            model="chat-test", base_url="http://ollama.test:11434", context_window=8192
        )

        self.assertEqual(provider.generate("prompt", temperature=0.2, max_tokens=25), "local answer")
        model.bind.assert_called_once_with(
            options={"temperature": 0.2, "num_predict": 25, "num_ctx": 8192}
        )
        model.bind.return_value.invoke.assert_called_once_with("prompt")

    @patch("providers.ollama.ChatOllama")
    def test_ollama_structured_adapter_forwards_schema_and_disables_thinking(
        self, chat_class: Mock
    ) -> None:
        model = chat_class.return_value
        model.bind.return_value.invoke.return_value = SimpleNamespace(
            content='{"decision":"CAN_ANSWER","explanation":"grounded"}'
        )
        schema = RelevanceResult.model_json_schema()
        provider = OllamaChatProvider(
            model="chat-test", base_url="http://ollama.test:11434", context_window=8192
        )

        self.assertEqual(
            provider.generate_structured(
                "prompt", schema=schema, temperature=0.2, max_tokens=25
            ),
            '{"decision":"CAN_ANSWER","explanation":"grounded"}',
        )
        model.bind.assert_called_once_with(
            format=schema,
            think=False,
            options={"temperature": 0.2, "num_predict": 25, "num_ctx": 8192},
        )

    @patch("providers.ollama.ChatOllama")
    def test_ollama_structured_adapter_rejects_empty_content(self, chat_class: Mock) -> None:
        chat_class.return_value.bind.return_value.invoke.return_value = SimpleNamespace(
            content="", thinking="untrusted reasoning"
        )
        provider = OllamaChatProvider(
            model="chat-test", base_url="http://ollama.test:11434", context_window=8192
        )

        with self.assertRaises(OllamaProviderError):
            provider.generate_structured(
                "prompt", schema=RelevanceResult.model_json_schema(), temperature=0, max_tokens=25
            )

    @patch("providers.ollama.ChatOllama")
    def test_ollama_chat_adapter_wraps_unavailable_service(self, chat_class: Mock) -> None:
        chat_class.return_value.bind.side_effect = OSError("connection refused")
        provider = OllamaChatProvider(
            model="chat-test", base_url="http://ollama.test:11434", context_window=8192
        )

        with self.assertRaises(OllamaProviderError):
            provider.generate("prompt", temperature=0, max_tokens=1)

    @patch("providers.ollama.OllamaEmbeddings")
    def test_ollama_embedding_adapter_wraps_unavailable_service(self, embeddings_class: Mock) -> None:
        embeddings_class.return_value.embed_query.side_effect = OSError("connection refused")
        provider = OllamaEmbeddingProvider(
            model="embed-test", base_url="http://ollama.test:11434", batch_size=2
        )

        with self.assertRaises(OllamaProviderError):
            provider.embed_query("question")

    @patch("providers.ollama.OllamaEmbeddings")
    def test_embedding_batches_are_ordered_and_include_final_partial_batch(
        self, embeddings_class: Mock
    ) -> None:
        model = embeddings_class.return_value
        model.embed_documents.side_effect = lambda batch: [[float(ord(text))] for text in batch]
        provider = OllamaEmbeddingProvider(
            model="embed-test", base_url="http://ollama.test:11434", batch_size=2
        )

        result = provider.embed_documents(["a", "b", "c", "d", "e"])

        self.assertEqual(result, [[97.0], [98.0], [99.0], [100.0], [101.0]])
        self.assertEqual(
            [call.args[0] for call in model.embed_documents.call_args_list],
            [["a", "b"], ["c", "d"], ["e"]],
        )
        self.assertEqual(provider.embed_documents([]), [])
        self.assertEqual(model.embed_documents.call_count, 3)

    @patch("providers.ollama.OllamaEmbeddings")
    def test_embedding_middle_batch_failure_returns_no_partial_embeddings(self, embeddings_class: Mock) -> None:
        model = embeddings_class.return_value
        model.embed_documents.side_effect = [[[1.0], [2.0]], OSError("provider unavailable")]
        provider = OllamaEmbeddingProvider(
            model="embed-test", base_url="http://ollama.test:11434", batch_size=2
        )

        with self.assertRaisesRegex(OllamaProviderError, "embedding request failed"):
            provider.embed_documents(["a", "b", "c"])

        self.assertEqual(
            [call.args[0] for call in model.embed_documents.call_args_list],
            [["a", "b"], ["c"]],
        )

    @patch("providers.ollama.OllamaEmbeddings")
    def test_embedding_response_count_mismatch_is_safe_and_query_behavior_is_unchanged(
        self, embeddings_class: Mock
    ) -> None:
        model = embeddings_class.return_value
        model.embed_documents.return_value = [[1.0]]
        model.embed_query.return_value = [3.0, 4.0]
        provider = OllamaEmbeddingProvider(
            model="embed-test", base_url="http://ollama.test:11434", batch_size=2
        )

        with self.assertRaisesRegex(OllamaProviderError, "did not match"):
            provider.embed_documents(["a", "b"])
        self.assertEqual(provider.embed_query("question"), [3.0, 4.0])
        model.embed_query.assert_called_once_with("question")

    def test_hybrid_retriever_keeps_bm25_and_vector_retrieval(self) -> None:
        documents = [
            Document(
                page_content="DocChat preserves hybrid retrieval.",
                metadata={"document_id": "docchat", "chunk_id": "docchat-hybrid"},
            ),
            Document(
                page_content="Ollama runs locally.",
                metadata={"document_id": "ollama", "chunk_id": "ollama-local"},
            ),
        ]
        with TemporaryDirectory() as temporary_directory:
            config = Settings(_env_file=None, CHROMA_DB_PATH=temporary_directory, VECTOR_SEARCH_K=2)
            retriever = RetrieverBuilder(FakeEmbeddingProvider(), config).build_hybrid_retriever(documents)
            result = retriever.invoke("How does DocChat retrieve documents?")

        self.assertGreater(len(result), 0)

    def test_workflow_uses_injected_chat_provider_without_vendor_sdk(self) -> None:
        provider = FakeChatProvider(
            [
                json.dumps({"decision": "CAN_ANSWER", "explanation": "grounded"}),
                json.dumps({"draft_answer": "DocChat uses a hybrid retriever."}),
                json.dumps(
                    {
                        "supported": True,
                        "relevant": True,
                        "unsupported_claims": [],
                        "contradictions": [],
                        "correction_feedback": "grounded",
                    }
                ),
            ]
        )
        workflow = AgentWorkflow(provider)

        result = workflow.full_pipeline(
            question="How does DocChat retrieve documents?",
            retriever=FakeRetriever([Document(page_content="DocChat uses BM25 and vector retrieval.")]),
        )

        self.assertEqual(result["draft_answer"], "DocChat uses a hybrid retriever.")
        self.assertIn("**Supported:** YES", result["verification_report"])
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(
            [call["schema"] for call in provider.calls],
            [
                RelevanceResult.model_json_schema(),
                ResearchResult.model_json_schema(),
                VerificationResult.model_json_schema(),
            ],
        )

    def test_active_core_modules_do_not_import_ibm_or_openai_sdks(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        core_modules = [
            repository_root / "app.py",
            repository_root / "retriever" / "builder.py",
            *sorted((repository_root / "agents").glob("*.py")),
        ]
        forbidden_imports = ("ibm_watsonx_ai", "langchain_ibm", "langchain_openai")

        for module in core_modules:
            source = module.read_text(encoding="utf-8")
            self.assertFalse(
                any(forbidden in source for forbidden in forbidden_imports),
                msg=f"Vendor SDK import found in {module.relative_to(repository_root)}",
            )
