"""Focused V1-C04 tests for typed agent contracts and workflow routing."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.contracts import RelevanceDecision, RelevanceResult, StructuredOutputError
from agents.workflow import AgentWorkflow
from config.settings import Settings


class FakeChatProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        self.calls.append({"prompt": prompt, "temperature": temperature, "max_tokens": max_tokens})
        return next(self.responses)

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        del schema
        return self.generate(prompt, temperature=temperature, max_tokens=max_tokens)


class FakeRetriever:
    def invoke(self, _: str) -> list[Document]:
        return [Document(page_content="DocChat combines BM25 and vector retrieval.")]


def relevance(decision: str, explanation: str = "test relevance") -> str:
    return json.dumps({"decision": decision, "explanation": explanation})


def research(answer: str) -> str:
    return json.dumps({"draft_answer": answer})


def verification(
    supported: bool,
    relevant: bool = True,
    feedback: str = "test feedback",
) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": relevant,
            "unsupported_claims": [] if supported else ["unsupported claim"],
            "contradictions": [],
            "correction_feedback": feedback,
        }
    )


class StructuredContractTests(TestCase):
    def workflow(self, responses: list[str], retries: int = 2) -> tuple[AgentWorkflow, FakeChatProvider]:
        provider = FakeChatProvider(responses)
        config = Settings(_env_file=None, MAX_VERIFICATION_RETRIES=retries)
        return AgentWorkflow(provider, config), provider

    def test_relevance_result_is_typed_and_routes_partial_to_research(self) -> None:
        result = RelevanceResult.from_model_json(relevance("PARTIAL"))
        self.assertEqual(result.decision, RelevanceDecision.PARTIAL)
        self.assertTrue(result.is_relevant)

        workflow, provider = self.workflow(
            [relevance("PARTIAL"), research("partial answer"), verification(True)]
        )
        final = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(final["terminal_outcome"], "VERIFIED")
        self.assertEqual(len(provider.calls), 3)

    def test_verification_boolean_controls_retry_then_verified_route(self) -> None:
        workflow, provider = self.workflow(
            [
                relevance("CAN_ANSWER"),
                research("first answer"),
                verification(False),
                research("corrected answer"),
                verification(True),
            ],
            retries=1,
        )

        final = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(final["terminal_outcome"], "VERIFIED")
        self.assertEqual(final["verification_retries"], 1)
        self.assertEqual(len(provider.calls), 5)

    def test_retry_exhaustion_uses_typed_verification_status(self) -> None:
        workflow, _ = self.workflow(
            [
                relevance("CAN_ANSWER"),
                research("first answer"),
                verification(False),
                research("second answer"),
                verification(False),
            ],
            retries=1,
        )

        final = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(final["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertEqual(final["verification_retries"], 1)
        self.assertEqual(final["draft_answer"], "second answer")

    def test_human_readable_feedback_cannot_change_typed_verified_route(self) -> None:
        workflow, _ = self.workflow(
            [
                relevance("CAN_ANSWER"),
                research("answer"),
                verification(True, feedback="**Supported:** NO is only quoted text."),
            ]
        )

        final = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(final["terminal_outcome"], "VERIFIED")

    def test_malformed_verification_json_terminates_as_explicit_failure(self) -> None:
        workflow, provider = self.workflow(
            [relevance("CAN_ANSWER"), research("answer"), "Supported: YES"],
            retries=2,
        )

        final = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(final["terminal_outcome"], "FAILURE")
        self.assertIn("malformed structured output", final["verification_report"])
        self.assertEqual(final["verification_retries"], 0)
        self.assertEqual(len(provider.calls), 3)

    def test_malformed_contract_is_rejected_instead_of_coerced(self) -> None:
        with self.assertRaises(StructuredOutputError):
            RelevanceResult.from_model_json('{"decision":"CAN_ANSWER","explanation":3}')
