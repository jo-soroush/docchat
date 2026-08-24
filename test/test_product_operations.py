"""Focused V1-C10 tests for thin study-operation routing."""

from unittest import TestCase

from product.operations import (
    OPERATION_LABELS,
    OPERATION_INTENTS,
    OperationInputError,
    ResearchOperation,
    build_operation_request,
    build_operation_question,
    gradio_operation_choices,
    run_operation,
)


class RecordingWorkflow:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.result = {
            "terminal_outcome": "VERIFIED",
            "citations": [{"chunk_id": "evidence-1", "available": True}],
            "verification_retries": 0,
            "run_trace": {"run_id": "safe-run"},
        }

    def full_pipeline(self, question: str, retriever: object, **kwargs) -> dict:
        self.calls.append((question, retriever, kwargs))
        return self.result


class ProductOperationTests(TestCase):
    def test_all_required_operations_have_stable_gradio_choices(self) -> None:
        self.assertEqual(
            gradio_operation_choices(),
            [(OPERATION_LABELS[operation], operation.value) for operation in ResearchOperation],
        )

    def test_ask_preserves_the_user_question(self) -> None:
        self.assertEqual(
            build_operation_question(ResearchOperation.ASK.value, "What does the paper conclude?"),
            "What does the paper conclude?",
        )

    def test_study_operations_build_deterministic_backend_questions(self) -> None:
        cases = {
            ResearchOperation.SUMMARIZE: "Summarize the uploaded document(s). Focus on: methods",
            ResearchOperation.KEY_POINTS: "List the key points from the uploaded document(s).",
            ResearchOperation.COMPARE_SOURCES: "Compare the uploaded document sources. Focus on: cost and reliability",
            ResearchOperation.EXPLAIN_CONCEPT: "Explain the concept 'hybrid retrieval' using the uploaded document(s).",
            ResearchOperation.STUDY_QUESTIONS: "Generate study questions from the uploaded document(s).",
        }
        inputs = {
            ResearchOperation.SUMMARIZE: "methods",
            ResearchOperation.KEY_POINTS: "",
            ResearchOperation.COMPARE_SOURCES: "cost and reliability",
            ResearchOperation.EXPLAIN_CONCEPT: "hybrid retrieval",
            ResearchOperation.STUDY_QUESTIONS: "",
        }
        for operation, expected_question in cases.items():
            with self.subTest(operation=operation):
                self.assertEqual(build_operation_question(operation.value, inputs[operation]), expected_question)

    def test_all_operations_preserve_typed_evidence_intent(self) -> None:
        expected = {
            ResearchOperation.ASK: "QUESTION",
            ResearchOperation.EXPLAIN_CONCEPT: "QUESTION",
            ResearchOperation.SUMMARIZE: "DOCUMENT_SYNTHESIS",
            ResearchOperation.KEY_POINTS: "DOCUMENT_SYNTHESIS",
            ResearchOperation.STUDY_QUESTIONS: "DOCUMENT_SYNTHESIS",
            ResearchOperation.COMPARE_SOURCES: "MULTI_DOCUMENT_COMPARISON",
        }
        for operation, intent in expected.items():
            focus = "topic" if operation in {ResearchOperation.ASK, ResearchOperation.EXPLAIN_CONCEPT} else ""
            with self.subTest(operation=operation):
                request = build_operation_request(operation.value, focus)
                self.assertEqual(request.operation, operation)
                self.assertEqual(request.evidence_intent, OPERATION_INTENTS[operation])
                self.assertEqual(request.evidence_intent.value, intent)

    def test_required_operation_input_and_unknown_operation_fail_safely(self) -> None:
        with self.assertRaisesRegex(OperationInputError, "Enter a question"):
            build_operation_question(ResearchOperation.ASK.value, "")
        with self.assertRaisesRegex(OperationInputError, "Enter a concept"):
            build_operation_question(ResearchOperation.EXPLAIN_CONCEPT.value, "")
        with self.assertRaisesRegex(OperationInputError, "supported research operation"):
            build_operation_question("unsupported", "anything")

    def test_operation_dispatches_once_to_existing_workflow_without_changing_result(self) -> None:
        workflow = RecordingWorkflow()
        retriever = object()
        result = run_operation(
            ResearchOperation.STUDY_QUESTIONS.value, "retrieval concepts", workflow, retriever
        )
        self.assertIs(result, workflow.result)
        self.assertEqual(
            workflow.calls,
            [
                (
                    "Generate study questions from the uploaded document(s). Focus on: retrieval concepts",
                    retriever,
                    {
                        "evidence_intent": OPERATION_INTENTS[ResearchOperation.STUDY_QUESTIONS],
                        "operation": ResearchOperation.STUDY_QUESTIONS.value,
                    },
                )
            ],
        )
        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(result["citations"][0]["chunk_id"], "evidence-1")
        self.assertEqual(result["verification_retries"], 0)
        self.assertEqual(result["run_trace"]["run_id"], "safe-run")
