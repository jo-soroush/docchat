from dataclasses import dataclass
import logging
from typing import Any

from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from config.settings import Settings, settings
from providers.contracts import EmbeddingProvider
from .evidence import ActiveDocumentEvidenceRetriever

logger = logging.getLogger(__name__)


class RetrievalError(RuntimeError):
    """Safe failure while constructing DocChat retrieval components."""


@dataclass(frozen=True)
class RetrievalModes:
    """Comparable retrievers built from the same documents and common result limit."""

    bm25: BM25Retriever
    vector: Any
    hybrid: EnsembleRetriever


class RetrieverBuilder:
    def __init__(self, embeddings: EmbeddingProvider, config: Settings = settings):
        """Initialize with an injected embedding provider and retrieval settings."""
        self.embeddings = embeddings
        self.config = config
        
    def build_hybrid_retriever(self, docs):
        """Build the established production hybrid retriever without changing its limits."""
        active_documents = list(docs)
        modes = self._build_modes(
            active_documents,
            bm25_k=BM25Retriever.model_fields["k"].default,
            vector_k=self.config.VECTOR_SEARCH_K,
        )
        return ActiveDocumentEvidenceRetriever(
            modes.hybrid,
            active_documents,
            self.config.SYNTHESIS_EVIDENCE_MAX_CHUNKS,
        )

    def build_evaluation_modes(self, docs, k: int) -> RetrievalModes:
        """Build fair BM25/vector/hybrid comparators at one explicit evaluation K."""
        if k < 1:
            raise ValueError("Evaluation retrieval K must be at least 1.")
        return self._build_modes(docs, bm25_k=k, vector_k=k)

    def _build_modes(self, docs, *, bm25_k: int, vector_k: int) -> RetrievalModes:
        """Construct all retrieval modes while keeping their common ownership here."""
        try:
            chunk_ids, document_ids = self._stable_vector_identity(docs)

            # The stable C05 chunk ID is the Chroma record ID. Re-ingestion therefore
            # upserts the same logical record instead of accumulating duplicates.
            # The configured collection deliberately separates this scoped format
            # from legacy default-collection data without deleting it.
            vector_store = Chroma.from_documents(
                documents=docs,
                embedding=self.embeddings,
                ids=chunk_ids,
                collection_name=self.config.CHROMA_COLLECTION_NAME,
                persist_directory=self.config.CHROMA_DB_PATH,
            )
            logger.info("Vector store created successfully.")
            
            # Create BM25 retriever
            bm25 = BM25Retriever.from_documents(docs, k=bm25_k)
            logger.info("BM25 retriever created successfully.")
            
            # Create vector-based retriever
            vector_retriever = vector_store.as_retriever(
                search_kwargs={
                    "k": vector_k,
                    "filter": {"document_id": {"$in": document_ids}},
                }
            )
            logger.info("Vector retriever created successfully.")
            
            # Combine retrievers into a hybrid retriever
            hybrid_retriever = EnsembleRetriever(
                retrievers=[bm25, vector_retriever],
                weights=self.config.HYBRID_RETRIEVER_WEIGHTS
            )
            logger.info("Hybrid retriever created successfully.")
            return RetrievalModes(
                bm25=bm25,
                vector=vector_retriever,
                hybrid=hybrid_retriever,
            )
        except Exception as exc:
            logger.error("Failed to build hybrid retriever.")
            raise RetrievalError("Document retrieval could not be initialized.") from exc

    @staticmethod
    def _stable_vector_identity(docs) -> tuple[list[str], list[str]]:
        """Return existing C05 IDs required for idempotent, scoped vector storage."""
        chunk_ids: list[str] = []
        document_ids: list[str] = []
        for document in docs:
            metadata = document.metadata or {}
            chunk_id = metadata.get("chunk_id")
            document_id = metadata.get("document_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError("Every vector document must have a stable chunk_id.")
            if not isinstance(document_id, str) or not document_id:
                raise ValueError("Every vector document must have a stable document_id.")
            if chunk_id in chunk_ids:
                raise ValueError("Vector document chunk_id values must be unique.")
            chunk_ids.append(chunk_id)
            if document_id not in document_ids:
                document_ids.append(document_id)
        return chunk_ids, document_ids
