from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .constants import MAX_FILE_SIZE, MAX_TOTAL_SIZE, ALLOWED_TYPES

class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Local provider settings. Model values are defaults, not credentials.
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    # Bound each local embedding request without exposing batching to retrieval.
    OLLAMA_EMBEDDING_BATCH_SIZE: int = Field(default=32, ge=1, le=256)
    # Local context capacity forwarded only by the Ollama chat adapter.
    OLLAMA_CONTEXT_WINDOW: int = Field(default=8192, ge=1024, le=65536)

    # Gradio binds locally by default; override for a local port conflict.
    GRADIO_SERVER_PORT: int = Field(default=7860, ge=1, le=65535)

    # Re-research attempts after the initial research/verification pass.
    MAX_VERIFICATION_RETRIES: int = Field(default=2, ge=0, le=5)

    # Optional settings with defaults
    MAX_FILE_SIZE: int = MAX_FILE_SIZE
    MAX_TOTAL_SIZE: int = MAX_TOTAL_SIZE
    ALLOWED_TYPES: list = ALLOWED_TYPES

    # Database settings
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = Field(default="documents", min_length=1)

    # Retrieval settings
    VECTOR_SEARCH_K: int = 10
    HYBRID_RETRIEVER_WEIGHTS: list[float] = Field(default_factory=lambda: [0.4, 0.6])
    SYNTHESIS_EVIDENCE_MAX_CHUNKS: int = Field(default=12, ge=1, le=64)

    # Logging settings
    LOG_LEVEL: str = "INFO"

    # New cache settings with type annotations
    CACHE_DIR: str = "document_cache"
    CACHE_EXPIRE_DAYS: int = 7

    # Header-based parsing can produce very large sections. Keep each derived
    # chunk below a conservative, provider-neutral character boundary before
    # it reaches an embedding implementation.
    DOCUMENT_CHUNK_MAX_CHARACTERS: int = Field(default=4000, ge=256, le=16000)

settings = Settings()
