from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from config.settings import Settings, settings
from providers.contracts import EmbeddingProvider
import logging

logger = logging.getLogger(__name__)

class RetrieverBuilder:
    def __init__(self, embeddings: EmbeddingProvider, config: Settings = settings):
        """Initialize with an injected embedding provider and retrieval settings."""
        self.embeddings = embeddings
        self.config = config
        
    def build_hybrid_retriever(self, docs):
        """Build a hybrid retriever using BM25 and vector-based retrieval."""
        try:
            # Create Chroma vector store
            vector_store = Chroma.from_documents(
                documents=docs,
                embedding=self.embeddings,
                persist_directory=self.config.CHROMA_DB_PATH
            )
            logger.info("Vector store created successfully.")
            
            # Create BM25 retriever
            bm25 = BM25Retriever.from_documents(docs)
            logger.info("BM25 retriever created successfully.")
            
            # Create vector-based retriever
            vector_retriever = vector_store.as_retriever(search_kwargs={"k": self.config.VECTOR_SEARCH_K})
            logger.info("Vector retriever created successfully.")
            
            # Combine retrievers into a hybrid retriever
            hybrid_retriever = EnsembleRetriever(
                retrievers=[bm25, vector_retriever],
                weights=self.config.HYBRID_RETRIEVER_WEIGHTS
            )
            logger.info("Hybrid retriever created successfully.")
            return hybrid_retriever
        except Exception as e:
            logger.error(f"Failed to build hybrid retriever: {e}")
            raise
