"""Narrow vendor-neutral contracts consumed by DocChat core."""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Safe provider-boundary failure exposed to DocChat core."""


class ChatProvider(Protocol):
    """Generate one text response from a complete prompt."""

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        """Return generated text or raise a provider error."""

    def generate_structured(
        self,
        prompt: str,
        *,
        schema: Mapping[str, Any],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Return schema-constrained JSON text or raise a provider error."""


class EmbeddingProvider(Protocol):
    """LangChain-compatible synchronous embedding operations used by Chroma."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed source-document texts."""

    def embed_query(self, text: str) -> list[float]:
        """Embed one retrieval query."""
