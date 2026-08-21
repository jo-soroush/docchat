"""Focused V1-C02 tests for the vendor-neutral provider boundary."""

import json
from pathlib import Path
import os
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from langchain.schema import Document

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

    def test_configuration_builds_local_provider_bundle_without_credentials(self) -> None:
        config = Settings(
            _env_file=None,
            OLLAMA_BASE_URL="http://ollama.test:11434",
            OLLAMA_CHAT_MODEL="chat-test",
            OLLAMA_EMBEDDING_MODEL="embed-test",
        )

        bundle = build_runtime_providers(config)

        self.assertEqual(bundle.chat._model.model, "chat-test")
        self.assertEqual(bundle.chat._model.base_url, "http://ollama.test:11434")
        self.assertEqual(bundle.embeddings._embeddings.model, "embed-test")

    @patch("providers.ollama.ChatOllama")
    def test_ollama_chat_adapter_returns_text_and_passes_generation_options(self, chat_class: Mock) -> None:
        model = chat_class.return_value
        model.bind.return_value.invoke.return_value = SimpleNamespace(content=" local answer ")

        provider = OllamaChatProvider(model="chat-test", base_url="http://ollama.test:11434")

        self.assertEqual(provider.generate("prompt", temperature=0.2, max_tokens=25), "local answer")
        model.bind.assert_called_once_with(
            options={"temperature": 0.2, "num_predict": 25}
        )
        model.bind.return_value.invoke.assert_called_once_with("prompt")

    @patch("providers.ollama.ChatOllama")
    def test_ollama_chat_adapter_wraps_unavailable_service(self, chat_class: Mock) -> None:
        chat_class.return_value.bind.side_effect = OSError("connection refused")
        provider = OllamaChatProvider(model="chat-test", base_url="http://ollama.test:11434")

        with self.assertRaises(OllamaProviderError):
            provider.generate("prompt", temperature=0, max_tokens=1)

    @patch("providers.ollama.OllamaEmbeddings")
    def test_ollama_embedding_adapter_wraps_unavailable_service(self, embeddings_class: Mock) -> None:
        embeddings_class.return_value.embed_query.side_effect = OSError("connection refused")
        provider = OllamaEmbeddingProvider(model="embed-test", base_url="http://ollama.test:11434")

        with self.assertRaises(OllamaProviderError):
            provider.embed_query("question")

    def test_hybrid_retriever_keeps_bm25_and_vector_retrieval(self) -> None:
        documents = [
            Document(page_content="DocChat preserves hybrid retrieval."),
            Document(page_content="Ollama runs locally."),
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
