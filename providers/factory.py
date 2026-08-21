"""Runtime composition for the configured provider implementation."""

from dataclasses import dataclass

from config.settings import Settings, settings

from .contracts import ChatProvider, EmbeddingProvider
from .ollama import OllamaChatProvider, OllamaEmbeddingProvider


@dataclass(frozen=True)
class ProviderBundle:
    """The chat and embedding capabilities required by the DocChat application."""

    chat: ChatProvider
    embeddings: EmbeddingProvider


def build_runtime_providers(config: Settings = settings) -> ProviderBundle:
    """Build the configured local runtime without exposing vendor details to core."""
    return ProviderBundle(
        chat=OllamaChatProvider(
            model=config.OLLAMA_CHAT_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        ),
        embeddings=OllamaEmbeddingProvider(
            model=config.OLLAMA_EMBEDDING_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        ),
    )
