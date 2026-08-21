"""Narrow vendor-neutral contracts consumed by DocChat core."""

from typing import Protocol, Sequence


class ProviderError(RuntimeError):
    """Safe provider-boundary failure exposed to DocChat core."""


class ChatProvider(Protocol):
    """Generate one text response from a complete prompt."""

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        """Return generated text or raise a provider error."""


class EmbeddingProvider(Protocol):
    """LangChain-compatible synchronous embedding operations used by Chroma."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed source-document texts."""

    def embed_query(self, text: str) -> list[float]:
        """Embed one retrieval query."""
