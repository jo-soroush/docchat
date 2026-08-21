"""Focused V1-C07 regression tests for grounded answer/verification evaluation."""

from dataclasses import replace
from unittest import TestCase

from evaluation.answer_verification_fixtures import golden_answer_verification_cases
from evaluation.answer_verification_metrics import (
    REQUIRED_CATEGORIES,
    evaluate_case,
    evaluate_cases,
    validate_golden_answer_verification_cases,
)
from evaluation.run_answer_verification_evaluation import run_evaluation


class AnswerVerificationEvaluationTests(TestCase):
    def test_golden_cases_cover_the_exact_c07_contract_categories(self) -> None:
        cases = golden_answer_verification_cases()

        validate_golden_answer_verification_cases(cases)

        self.assertEqual({case.category for case in cases}, REQUIRED_CATEGORIES)
        self.assertEqual(len(cases), 10)
        self.assertTrue(all(document.metadata["chunk_id"] for case in cases for document in case.documents))

    def test_suite_separates_retrieval_answer_citation_and_verification_results(self) -> None:
        metrics = evaluate_cases(golden_answer_verification_cases())

        self.assertEqual(metrics.total_cases, 10)
        self.assertEqual(metrics.passed_cases, 10)
        self.assertEqual(metrics.retrieval_scored_cases, 9)
        self.assertEqual(metrics.retrieval_precondition_passed_cases, 9)
        self.assertEqual(metrics.answer_passed_cases, 10)
        self.assertEqual(metrics.citation_scored_cases, 9)
        self.assertEqual(metrics.citation_grounding_passed_cases, 9)
        self.assertEqual(metrics.verification_scored_cases, 9)
        self.assertEqual(metrics.verification_decision_passed_cases, 9)
        self.assertEqual(metrics.routing_passed_cases, 10)
        self.assertEqual(metrics.verification_passed_cases, 10)

    def test_out_of_scope_is_a_terminal_behavior_not_a_retrieval_score(self) -> None:
        case = next(case for case in golden_answer_verification_cases() if case.category == "out_of_scope")

        result = evaluate_case(case)

        self.assertTrue(result.passed)
        self.assertIsNone(result.retrieval_precondition_passed)
        self.assertIsNone(result.citation_grounding_passed)
        self.assertIsNone(result.verification_decision_passed)
        self.assertEqual(result.terminal_outcome, "OUT_OF_SCOPE")
        self.assertEqual(result.verification_retries, 0)

    def test_correction_and_retry_exhaustion_are_deterministic(self) -> None:
        cases = {case.category: case for case in golden_answer_verification_cases()}

        correction = evaluate_case(cases["correction_success"])
        exhausted = evaluate_case(cases["retry_exhaustion"])

        self.assertEqual((correction.terminal_outcome, correction.verification_retries), ("VERIFIED", 1))
        self.assertEqual((exhausted.terminal_outcome, exhausted.verification_retries), ("RETRY_EXHAUSTED", 2))
        self.assertTrue(correction.passed)
        self.assertTrue(exhausted.passed)

    def test_missing_expected_retrieval_evidence_fails_instead_of_hiding_regression(self) -> None:
        case = next(case for case in golden_answer_verification_cases() if case.category == "answerable")
        incomplete_case = replace(case, expected_chunk_ids=frozenset({"missing-evidence"}))

        with self.assertRaises(ValueError):
            validate_golden_answer_verification_cases([incomplete_case, *golden_answer_verification_cases()[1:]])

    def test_runner_is_repeatable(self) -> None:
        first = run_evaluation()
        second = run_evaluation()

        self.assertEqual(first, second)
        self.assertEqual(first["answer_verification"]["passed_cases"], 10)
        self.assertEqual(set(first["retrieval"]), {"bm25", "vector", "hybrid"})
