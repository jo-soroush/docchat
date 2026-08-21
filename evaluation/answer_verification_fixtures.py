"""Version-controlled golden workflow cases for V1-C07 evaluation."""

from dataclasses import dataclass
import json

from langchain.schema import Document


@dataclass(frozen=True)
class GoldenAnswerVerificationCase:
    """One deterministic workflow behavior with expected stable evidence IDs."""

    case_id: str
    category: str
    question: str
    documents: tuple[Document, ...]
    expected_chunk_ids: frozenset[str]
    expected_answer: str
    expected_supported: bool | None
    expected_terminal_outcome: str
    expected_retries: int
    expected_citation_chunk_ids: frozenset[str]
    responses: tuple[str, ...]
    out_of_scope: bool = False


class FixtureChatProvider:
    """Deterministic ChatProvider fake used by the C07 evaluation runner."""

    def __init__(self, responses: tuple[str, ...]) -> None:
        self._responses = iter(responses)
        self.calls = 0

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        del prompt, temperature, max_tokens
        self.calls += 1
        return next(self._responses)


class FixtureRetriever:
    """Static retrieved evidence for one golden workflow case."""

    def __init__(self, documents: tuple[Document, ...]) -> None:
        self.documents = list(documents)

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def golden_answer_verification_cases() -> list[GoldenAnswerVerificationCase]:
    """Return the ten behavior classes mandated by the V1-C07 Card contract."""
    hybrid = _document(
        "retrieval-guide",
        "retrieval-hybrid",
        "retrieval.md",
        "Hybrid Retrieval",
        "DocChat combines BM25 lexical retrieval with vector similarity retrieval.",
    )
    bm25 = _document(
        "retrieval-guide",
        "retrieval-bm25",
        "retrieval.md",
        "Lexical Retrieval",
        "BM25 provides lexical keyword retrieval using token matching.",
    )
    retry_limit = _document(
        "workflow-guide",
        "workflow-retry-limit",
        "workflow.md",
        "Bounded Verification",
        "The configured verification retry limit in this fixture is two re-research attempts.",
    )
    ollama = _document(
        "runtime-guide",
        "runtime-ollama",
        "runtime.md",
        "Local Runtime",
        "Ollama is the local runtime behind DocChat's provider boundary.",
    )
    typed = _document(
        "workflow-guide",
        "workflow-contracts",
        "workflow.md",
        "Typed Workflow",
        "Pydantic contracts keep verification workflow routing deterministic.",
    )

    return [
        _case(
            "answerable-hybrid",
            "answerable",
            "How does DocChat retrieve document evidence?",
            (hybrid,),
            {"retrieval-hybrid"},
            "DocChat combines BM25 lexical retrieval with vector similarity retrieval.",
            True,
            "VERIFIED",
            0,
            {"retrieval-hybrid"},
            (_relevance("CAN_ANSWER"), _research("DocChat combines BM25 lexical retrieval with vector similarity retrieval.", {"DocChat combines BM25 lexical retrieval with vector similarity retrieval.": ["retrieval-hybrid"]}), _verification(True)),
        ),
        _case(
            "partial-bm25",
            "partial",
            "What does the document say about DocChat retrieval?",
            (bm25,),
            {"retrieval-bm25"},
            "The available context states that BM25 provides lexical keyword retrieval using token matching.",
            True,
            "VERIFIED",
            0,
            {"retrieval-bm25"},
            (_relevance("PARTIAL"), _research("The available context states that BM25 provides lexical keyword retrieval using token matching.", {"The available context states that BM25 provides lexical keyword retrieval using token matching.": ["retrieval-bm25"]}), _verification(True)),
        ),
        _case(
            "out-of-scope-geography",
            "out_of_scope",
            "What is the capital city of Sweden?",
            (hybrid,),
            frozenset(),
            "This question is not related to the uploaded document(s), or the documents do not contain enough information to answer it.",
            None,
            "OUT_OF_SCOPE",
            0,
            frozenset(),
            (_relevance("NO_MATCH"),),
            out_of_scope=True,
        ),
        _case(
            "numerical-error-corrected",
            "numerical_error",
            "How many re-research attempts does this fixture permit?",
            (retry_limit,),
            {"workflow-retry-limit"},
            "This fixture permits two re-research attempts.",
            True,
            "VERIFIED",
            1,
            {"workflow-retry-limit"},
            (
                _relevance("CAN_ANSWER"),
                _research("This fixture permits three re-research attempts.", {"This fixture permits three re-research attempts.": ["workflow-retry-limit"]}),
                _verification(False, unsupported=["The answer says three, but the evidence says two."], feedback="Correct the number to two."),
                _research("This fixture permits two re-research attempts.", {"This fixture permits two re-research attempts.": ["workflow-retry-limit"]}),
                _verification(True),
            ),
        ),
        _case(
            "unsupported-claim-corrected",
            "unsupported_claim",
            "Which local runtime is behind the provider boundary?",
            (ollama,),
            {"runtime-ollama"},
            "Ollama is the local runtime behind DocChat's provider boundary.",
            True,
            "VERIFIED",
            1,
            {"runtime-ollama"},
            (
                _relevance("CAN_ANSWER"),
                _research("The provider boundary runs on an unsupported cloud service.", {"The provider boundary runs on an unsupported cloud service.": ["runtime-ollama"]}),
                _verification(False, unsupported=["The cloud-service claim is unsupported."], feedback="State the local runtime named in the evidence."),
                _research("Ollama is the local runtime behind DocChat's provider boundary.", {"Ollama is the local runtime behind DocChat's provider boundary.": ["runtime-ollama"]}),
                _verification(True),
            ),
        ),
        _case(
            "contradiction-corrected",
            "contradiction",
            "Is BM25 a semantic similarity retriever?",
            (bm25,),
            {"retrieval-bm25"},
            "No. BM25 provides lexical keyword retrieval using token matching.",
            True,
            "VERIFIED",
            1,
            {"retrieval-bm25"},
            (
                _relevance("CAN_ANSWER"),
                _research("Yes. BM25 provides semantic similarity retrieval.", {"Yes. BM25 provides semantic similarity retrieval.": ["retrieval-bm25"]}),
                _verification(False, contradictions=["The evidence describes BM25 as lexical keyword retrieval."], feedback="Correct the lexical-versus-semantic distinction."),
                _research("No. BM25 provides lexical keyword retrieval using token matching.", {"No. BM25 provides lexical keyword retrieval using token matching.": ["retrieval-bm25"]}),
                _verification(True),
            ),
        ),
        _case(
            "multi-chunk-grounded",
            "multi_chunk",
            "Which retrieval methods are combined by DocChat?",
            (hybrid, bm25),
            {"retrieval-hybrid", "retrieval-bm25"},
            "DocChat combines BM25 lexical retrieval with vector similarity retrieval, and BM25 uses token matching.",
            True,
            "VERIFIED",
            0,
            {"retrieval-hybrid", "retrieval-bm25"},
            (_relevance("CAN_ANSWER"), _research("DocChat combines BM25 lexical retrieval with vector similarity retrieval, and BM25 uses token matching.", {"DocChat combines BM25 lexical retrieval with vector similarity retrieval": ["retrieval-hybrid"], "BM25 uses token matching": ["retrieval-bm25"]}), _verification(True)),
        ),
        _case(
            "multi-document-grounded",
            "multi_document",
            "Which local runtime and workflow safeguard does DocChat use?",
            (ollama, typed),
            {"runtime-ollama", "workflow-contracts"},
            "DocChat uses Ollama locally, and Pydantic contracts keep workflow routing deterministic.",
            True,
            "VERIFIED",
            0,
            {"runtime-ollama", "workflow-contracts"},
            (_relevance("CAN_ANSWER"), _research("DocChat uses Ollama locally, and Pydantic contracts keep workflow routing deterministic.", {"DocChat uses Ollama locally": ["runtime-ollama"], "Pydantic contracts keep workflow routing deterministic": ["workflow-contracts"]}), _verification(True)),
        ),
        _case(
            "correction-success",
            "correction_success",
            "What keeps workflow routing deterministic?",
            (typed,),
            {"workflow-contracts"},
            "Pydantic contracts keep verification workflow routing deterministic.",
            True,
            "VERIFIED",
            1,
            {"workflow-contracts"},
            (
                _relevance("CAN_ANSWER"),
                _research("Free-text reports keep workflow routing deterministic.", {"Free-text reports keep workflow routing deterministic.": ["workflow-contracts"]}),
                _verification(False, unsupported=["Free-text routing is unsupported."], feedback="Name the typed contracts."),
                _research("Pydantic contracts keep verification workflow routing deterministic.", {"Pydantic contracts keep verification workflow routing deterministic.": ["workflow-contracts"]}),
                _verification(True),
            ),
        ),
        _case(
            "retry-exhaustion",
            "retry_exhaustion",
            "What local runtime is behind DocChat?",
            (ollama,),
            {"runtime-ollama"},
            "The final unsupported draft remains after the retry budget is exhausted.",
            False,
            "RETRY_EXHAUSTED",
            2,
            {"runtime-ollama"},
            (
                _relevance("CAN_ANSWER"),
                _research("An unsupported runtime is used.", {"An unsupported runtime is used.": ["runtime-ollama"]}),
                _verification(False, unsupported=["The runtime claim is unsupported."], feedback="Use the named local runtime."),
                _research("A second unsupported runtime is used.", {"A second unsupported runtime is used.": ["runtime-ollama"]}),
                _verification(False, unsupported=["The runtime claim remains unsupported."], feedback="Use the named local runtime."),
                _research("The final unsupported draft remains after the retry budget is exhausted.", {"The final unsupported draft remains after the retry budget is exhausted.": ["runtime-ollama"]}),
                _verification(False, unsupported=["The runtime claim remains unsupported."], feedback="Use the named local runtime."),
            ),
        ),
    ]


def _case(
    case_id: str,
    category: str,
    question: str,
    documents: tuple[Document, ...],
    expected_chunk_ids: set[str] | frozenset[str],
    expected_answer: str,
    expected_supported: bool | None,
    expected_terminal_outcome: str,
    expected_retries: int,
    expected_citation_chunk_ids: set[str] | frozenset[str],
    responses: tuple[str, ...],
    out_of_scope: bool = False,
) -> GoldenAnswerVerificationCase:
    return GoldenAnswerVerificationCase(
        case_id=case_id,
        category=category,
        question=question,
        documents=documents,
        expected_chunk_ids=frozenset(expected_chunk_ids),
        expected_answer=expected_answer,
        expected_supported=expected_supported,
        expected_terminal_outcome=expected_terminal_outcome,
        expected_retries=expected_retries,
        expected_citation_chunk_ids=frozenset(expected_citation_chunk_ids),
        responses=responses,
        out_of_scope=out_of_scope,
    )


def _document(
    document_id: str, chunk_id: str, source_name: str, section: str, content: str
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


def _relevance(decision: str) -> str:
    return json.dumps({"decision": decision, "explanation": "fixture relevance result"})


def _research(answer: str, claim_sources: dict[str, list[str]]) -> str:
    return json.dumps(
        {
            "draft_answer": answer,
            "claim_sources": [
                {"claim": claim, "chunk_ids": chunk_ids}
                for claim, chunk_ids in claim_sources.items()
            ],
        }
    )


def _verification(
    supported: bool,
    *,
    unsupported: list[str] | None = None,
    contradictions: list[str] | None = None,
    feedback: str = "fixture verification result",
) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": True,
            "unsupported_claims": unsupported or [],
            "contradictions": contradictions or [],
            "correction_feedback": feedback,
        }
    )
