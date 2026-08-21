"""Small, version-controlled golden evidence for V1-C06 retrieval evaluation."""

from dataclasses import dataclass
import re

from langchain.schema import Document


@dataclass(frozen=True)
class GoldenRetrievalCase:
    case_id: str
    question: str
    expected_chunk_ids: frozenset[str]
    category: str
    out_of_scope: bool = False


class DeterministicKeywordEmbedding:
    """Tiny local embedding fake for repeatable retrieval tests and measurements."""

    _CONCEPTS = (
        {"bm25", "lexical", "keyword", "token"},
        {"vector", "semantic", "meaning", "similarity", "related"},
        {"ollama", "local", "runtime", "provider"},
        {"citation", "source", "chunk", "provenance"},
        {"pydantic", "typed", "verification", "workflow", "contract"},
    )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        return [float(len(tokens & concept)) for concept in self._CONCEPTS]


def golden_documents() -> list[Document]:
    """Return controlled multi-document chunks carrying C05-style stable identities."""
    return [
        _document(
            "runtime-guide",
            "runtime-ollama",
            "runtime.md",
            "Local Runtime",
            "Ollama is the local runtime behind DocChat's provider boundary.",
        ),
        _document(
            "retrieval-guide",
            "retrieval-bm25",
            "retrieval.md",
            "Lexical Retrieval",
            "BM25 provides lexical keyword retrieval using token matching.",
        ),
        _document(
            "retrieval-guide",
            "retrieval-vector",
            "retrieval.md",
            "Semantic Retrieval",
            "Vector retrieval finds semantically related passages by similarity.",
        ),
        _document(
            "provenance-guide",
            "provenance-citations",
            "provenance.md",
            "Citation Grounding",
            "Citations resolve each claim to a stable document chunk source.",
        ),
        _document(
            "workflow-guide",
            "workflow-contracts",
            "workflow.md",
            "Typed Workflow",
            "Pydantic contracts keep verification workflow routing deterministic.",
        ),
    ]


def golden_cases() -> list[GoldenRetrievalCase]:
    """Answerable, multi-document, and out-of-scope retrieval-only cases."""
    return [
        GoldenRetrievalCase(
            case_id="lexical-bm25",
            question="Which lexical keyword technique uses token matching?",
            expected_chunk_ids=frozenset({"retrieval-bm25"}),
            category="answerable",
        ),
        GoldenRetrievalCase(
            case_id="semantic-vector",
            question="How are meaning-related passages found?",
            expected_chunk_ids=frozenset({"retrieval-vector"}),
            category="answerable",
        ),
        GoldenRetrievalCase(
            case_id="citation-provenance",
            question="How can a claim be traced to a document source?",
            expected_chunk_ids=frozenset({"provenance-citations"}),
            category="answerable",
        ),
        GoldenRetrievalCase(
            case_id="multi-document-runtime-retrieval",
            question="Which local runtime and lexical retrieval technique does DocChat use?",
            expected_chunk_ids=frozenset({"runtime-ollama", "retrieval-bm25"}),
            category="multi_document",
        ),
        GoldenRetrievalCase(
            case_id="out-of-scope-geography",
            question="What is the capital city of Sweden?",
            expected_chunk_ids=frozenset(),
            category="out_of_scope",
            out_of_scope=True,
        ),
    ]


def _document(
    document_id: str,
    chunk_id: str,
    source_name: str,
    section: str,
    content: str,
) -> Document:
    return Document(
        page_content=content,
        metadata={
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source_name": source_name,
            "section": section,
        },
    )
