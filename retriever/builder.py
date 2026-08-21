from dataclasses import dataclass
import logging
from typing import Any

from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from config.settings import Settings, settings
from providers.contracts import EmbeddingProvider

logger = logging.getLogger(__name__)


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
        return self._build_modes(
            docs,
            bm25_k=BM25Retriever.model_fields["k"].default,
            vector_k=self.config.VECTOR_SEARCH_K,
        ).hybrid

    def build_evaluation_modes(self, docs, k: int) -> RetrievalModes:
        """Build fair BM25/vector/hybrid comparators at one explicit evaluation K."""
        if k < 1:
            raise ValueError("Evaluation retrieval K must be at least 1.")
        return self._build_modes(docs, bm25_k=k, vector_k=k)

    def _build_modes(self, docs, *, bm25_k: int, vector_k: int) -> RetrievalModes:
        """Construct all retrieval modes while keeping their common ownership here."""
        try:
            # Create Chroma vector store
            vector_store = Chroma.from_documents(
                documents=docs,
                embedding=self.embeddings,
                persist_directory=self.config.CHROMA_DB_PATH
            )
            logger.info("Vector store created successfully.")
            
            # Create BM25 retriever
            bm25 = BM25Retriever.from_documents(docs, k=bm25_k)
            logger.info("BM25 retriever created successfully.")
            
            # Create vector-based retriever
            vector_retriever = vector_store.as_retriever(search_kwargs={"k": vector_k})
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
        except Exception as e:
            logger.error(f"Failed to build hybrid retriever: {e}")
            raise
