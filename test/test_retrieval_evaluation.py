"""Focused V1-C06 tests for deterministic golden retrieval measurement."""

from tempfile import TemporaryDirectory
from unittest import TestCase

from langchain.schema import Document

from config.settings import Settings
from evaluation.retrieval_fixtures import (
    DeterministicKeywordEmbedding,
    GoldenRetrievalCase,
    golden_cases,
    golden_documents,
)
from evaluation.retrieval_metrics import evaluate_modes, evaluate_retriever, validate_golden_fixtures
from evaluation.run_retrieval_evaluation import EVALUATION_K, run_evaluation
from retriever.builder import RetrieverBuilder


class StaticRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


class RetrievalEvaluationTests(TestCase):
    def test_golden_fixtures_are_valid_and_cover_required_case_types(self) -> None:
        documents = golden_documents()
        cases = golden_cases()

        validate_golden_fixtures(cases, documents)

        self.assertTrue(any(case.category == "answerable" for case in cases))
        self.assertTrue(any(case.category == "multi_document" for case in cases))
        self.assertTrue(any(case.out_of_scope for case in cases))
        self.assertTrue(all(document.metadata["document_id"] for document in documents))
        self.assertTrue(all(document.metadata["chunk_id"] for document in documents))

    def test_invalid_golden_reference_is_rejected(self) -> None:
        documents = golden_documents()
        invalid_case = GoldenRetrievalCase(
            case_id="invalid",
            question="question",
            expected_chunk_ids=frozenset({"unknown"}),
            category="answerable",
        )

        with self.assertRaises(ValueError):
            validate_golden_fixtures([invalid_case], documents)

    def test_metrics_match_retrieved_stable_chunk_ids(self) -> None:
        document = golden_documents()[0]
        case = GoldenRetrievalCase(
            case_id="match",
            question="question",
            expected_chunk_ids=frozenset({document.metadata["chunk_id"]}),
            category="answerable",
        )

        result = evaluate_retriever("static", StaticRetriever([document]), [case], k=1)

        self.assertEqual(result.hit_rate_at_k, 1.0)
        self.assertEqual(result.mean_recall_at_k, 1.0)
        self.assertEqual(result.cases[0].matched_chunk_ids, (document.metadata["chunk_id"],))

    def test_out_of_scope_cases_are_recorded_but_excluded_from_quality_denominator(self) -> None:
        document = golden_documents()[0]
        case = GoldenRetrievalCase(
            case_id="outside",
            question="outside",
            expected_chunk_ids=frozenset(),
            category="out_of_scope",
            out_of_scope=True,
        )

        result = evaluate_retriever("static", StaticRetriever([document]), [case], k=1)

        self.assertEqual(result.scored_cases, 0)
        self.assertEqual(result.out_of_scope_cases, 1)
        self.assertIsNone(result.hit_rate_at_k)
        self.assertIsNone(result.mean_recall_at_k)
        self.assertIsNone(result.cases[0].hit_at_k)
        self.assertIsNone(result.cases[0].recall_at_k)

    def test_bm25_vector_and_hybrid_are_evaluated_at_the_same_k(self) -> None:
        documents = golden_documents()
        cases = golden_cases()
        with TemporaryDirectory() as directory:
            config = Settings(_env_file=None, CHROMA_DB_PATH=directory, VECTOR_SEARCH_K=EVALUATION_K)
            modes = RetrieverBuilder(DeterministicKeywordEmbedding(), config).build_evaluation_modes(
                documents, EVALUATION_K
            )
            results = evaluate_modes(modes, cases, EVALUATION_K)

        self.assertEqual(modes.bm25.k, EVALUATION_K)
        self.assertEqual(modes.vector.search_kwargs["k"], EVALUATION_K)
        self.assertEqual(set(results), {"bm25", "vector", "hybrid"})
        self.assertTrue(all(result.k == EVALUATION_K for result in results.values()))
        self.assertTrue(all(result.scored_cases == 4 for result in results.values()))
        self.assertTrue(all(result.out_of_scope_cases == 1 for result in results.values()))
        multi_document = next(
            case for case in results["hybrid"].cases if case.category == "multi_document"
        )
        self.assertEqual(len(multi_document.expected_chunk_ids), 2)

    def test_reproducible_runner_returns_all_mode_metrics(self) -> None:
        first = run_evaluation()
        second = run_evaluation()

        self.assertEqual(first, second)
        self.assertEqual(set(first), {"bm25", "vector", "hybrid"})
