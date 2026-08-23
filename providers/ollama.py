"""Ollama implementation details; this module is the vendor boundary."""

from collections.abc import Mapping, Sequence
from typing import Any

from langchain_ollama import ChatOllama, OllamaEmbeddings

from .contracts import ChatProvider, EmbeddingProvider, ProviderError


class OllamaProviderError(ProviderError):
    """Raised when the configured local Ollama service cannot complete a request."""


class OllamaChatProvider(ChatProvider):
    """Adapt LangChain's Ollama chat model to the DocChat chat contract."""

    def __init__(self, *, model: str, base_url: str) -> None:
        self._model = ChatOllama(model=model, base_url=base_url)

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        try:
            response = self._model.bind(
                options={"temperature": temperature, "num_predict": max_tokens},
            ).invoke(prompt)
        except Exception as exc:
            raise OllamaProviderError("Ollama chat request failed.") from exc

        return self._response_text(response)

    def generate_structured(
        self,
        prompt: str,
        *,
        schema: Mapping[str, Any],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Request native JSON-schema output without a model thinking channel."""
        try:
            response = self._model.bind(
                format=dict(schema),
                think=False,
                options={"temperature": temperature, "num_predict": max_tokens},
            ).invoke(prompt)
        except Exception as exc:
            raise OllamaProviderError("Ollama structured chat request failed.") from exc

        if self._structured_response_was_truncated(response):
            raise OllamaProviderError(
                "Ollama structured response exceeded its generation limit."
            )
        return self._response_text(response)

    @staticmethod
    def _structured_response_was_truncated(response) -> bool:
        """Recognize a provider completion limit without inspecting generated content."""
        metadata = getattr(response, "response_metadata", None)
        return isinstance(metadata, Mapping) and metadata.get("done_reason") == "length"

    @staticmethod
    def _response_text(response) -> str:
        content = response.content
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        raise OllamaProviderError("Ollama chat response did not contain text.")


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Adapt LangChain's Ollama embeddings to the DocChat embedding contract."""

    def __init__(self, *, model: str, base_url: str) -> None:
        self._embeddings = OllamaEmbeddings(model=model, base_url=base_url)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            return self._embeddings.embed_documents(list(texts))
        except Exception as exc:
            raise OllamaProviderError("Ollama embedding request failed.") from exc

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._embeddings.embed_query(text)
        except Exception as exc:
            raise OllamaProviderError("Ollama query embedding request failed.") from exc
