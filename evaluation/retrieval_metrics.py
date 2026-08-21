"""Deterministic metrics for comparing retrieval results against golden chunk IDs."""

from dataclasses import asdict, dataclass
from typing import Mapping

from .retrieval_fixtures import GoldenRetrievalCase


@dataclass(frozen=True)
class RetrievalCaseResult:
    case_id: str
    category: str
    expected_chunk_ids: tuple[str, ...]
    retrieved_chunk_ids: tuple[str, ...]
    matched_chunk_ids: tuple[str, ...]
    hit_at_k: bool | None
    recall_at_k: float | None
    out_of_scope: bool


@dataclass(frozen=True)
class RetrievalMetrics:
    mode: str
    k: int
    scored_cases: int
    out_of_scope_cases: int
    hit_rate_at_k: float | None
    mean_recall_at_k: float | None
    cases: tuple[RetrievalCaseResult, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_golden_fixtures(cases: list[GoldenRetrievalCase], documents: list) -> None:
    """Fail early when a gold ID is missing, duplicated, or misclassified."""
    chunk_ids = [document.metadata.get("chunk_id") for document in documents]
    if any(not isinstance(chunk_id, str) or not chunk_id for chunk_id in chunk_ids):
        raise ValueError("Every golden document must have a non-empty chunk_id.")
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Golden chunk IDs must be unique.")

    known_ids = set(chunk_ids)
    for case in cases:
        if case.out_of_scope != (not case.expected_chunk_ids):
            raise ValueError("Out-of-scope cases must have no expected chunk IDs.")
        unknown_ids = case.expected_chunk_ids - known_ids
        if unknown_ids:
            raise ValueError(f"Golden case {case.case_id} references unknown IDs: {unknown_ids}")


def evaluate_retriever(
    mode: str, retriever, cases: list[GoldenRetrievalCase], k: int
) -> RetrievalMetrics:
    """Measure ID overlap only; answers, citations, and verification are excluded."""
    if k < 1:
        raise ValueError("Evaluation K must be at least 1.")

    case_results: list[RetrievalCaseResult] = []
    for case in cases:
        retrieved_chunk_ids = _retrieved_chunk_ids(retriever.invoke(case.question), k)
        expected = set(case.expected_chunk_ids)
        matched = expected & set(retrieved_chunk_ids)
        if case.out_of_scope:
            hit_at_k = None
            recall_at_k = None
        else:
            hit_at_k = bool(matched)
            recall_at_k = len(matched) / len(expected)
        case_results.append(
            RetrievalCaseResult(
                case_id=case.case_id,
                category=case.category,
                expected_chunk_ids=tuple(sorted(expected)),
                retrieved_chunk_ids=tuple(retrieved_chunk_ids),
                matched_chunk_ids=tuple(sorted(matched)),
                hit_at_k=hit_at_k,
                recall_at_k=recall_at_k,
                out_of_scope=case.out_of_scope,
            )
        )

    scored = [result for result in case_results if not result.out_of_scope]
    hit_rate_at_k = None
    mean_recall_at_k = None
    if scored:
        hit_rate_at_k = sum(bool(result.hit_at_k) for result in scored) / len(scored)
        mean_recall_at_k = sum(result.recall_at_k or 0.0 for result in scored) / len(scored)

    return RetrievalMetrics(
        mode=mode,
        k=k,
        scored_cases=len(scored),
        out_of_scope_cases=len(case_results) - len(scored),
        hit_rate_at_k=hit_rate_at_k,
        mean_recall_at_k=mean_recall_at_k,
        cases=tuple(case_results),
    )


def evaluate_modes(modes, cases: list[GoldenRetrievalCase], k: int) -> Mapping[str, RetrievalMetrics]:
    """Evaluate all C06 retrieval modes against identical cases and K."""
    return {
        "bm25": evaluate_retriever("bm25", modes.bm25, cases, k),
        "vector": evaluate_retriever("vector", modes.vector, cases, k),
        "hybrid": evaluate_retriever("hybrid", modes.hybrid, cases, k),
    }


def _retrieved_chunk_ids(documents: list, k: int) -> list[str]:
    chunk_ids: list[str] = []
    for document in documents[:k]:
        chunk_id = document.metadata.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            raise ValueError("Retrieved evaluation document is missing chunk_id metadata.")
        if chunk_id not in chunk_ids:
            chunk_ids.append(chunk_id)
    return chunk_ids
