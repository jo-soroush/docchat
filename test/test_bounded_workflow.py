"""Focused V1-C03 tests for bounded research and verification routing."""

import json
import os
from unittest import TestCase

from langchain.schema import Document

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
    def __init__(self) -> None:
        self.documents = [Document(page_content="DocChat combines BM25 and vector retrieval.")]

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def relevance(decision: str) -> str:
    return json.dumps({"decision": decision, "explanation": "test relevance"})


def research(answer: str) -> str:
    return json.dumps({"draft_answer": answer})


def verification(supported: bool) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": True,
            "unsupported_claims": [],
            "contradictions": [],
            "correction_feedback": "test result",
        }
    )


class BoundedWorkflowTests(TestCase):
    def build_workflow(self, responses: list[str], retries: int) -> tuple[AgentWorkflow, FakeChatProvider]:
        provider = FakeChatProvider(responses)
        config = Settings(_env_file=None, MAX_VERIFICATION_RETRIES=retries)
        return AgentWorkflow(provider, config), provider

    def test_immediate_success_terminates_without_retry(self) -> None:
        workflow, provider = self.build_workflow(
            [relevance("CAN_ANSWER"), research("grounded answer"), verification(True)],
            retries=2,
        )

        result = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(result["verification_retries"], 0)
        self.assertEqual(len(provider.calls), 3)

    def test_failure_then_success_uses_one_retry(self) -> None:
        workflow, provider = self.build_workflow(
            [
                relevance("CAN_ANSWER"),
                research("first answer"),
                verification(False),
                research("corrected answer"),
                verification(True),
            ],
            retries=1,
        )

        result = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(result["verification_retries"], 1)
        self.assertEqual(result["draft_answer"], "corrected answer")
        self.assertEqual(len(provider.calls), 5)

    def test_repeated_failure_terminates_at_configured_budget(self) -> None:
        workflow, provider = self.build_workflow(
            [
                relevance("CAN_ANSWER"),
                research("first answer"),
                verification(False),
                research("second answer"),
                verification(False),
                research("third answer"),
                verification(False),
            ],
            retries=2,
        )

        result = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertEqual(result["verification_retries"], 2)
        self.assertEqual(result["draft_answer"], "third answer")
        self.assertIn("**Workflow Outcome:** RETRY_EXHAUSTED", result["verification_report"])
        self.assertEqual(len(provider.calls), 7)

    def test_zero_retry_limit_terminates_after_initial_failed_verification(self) -> None:
        workflow, provider = self.build_workflow(
            [relevance("CAN_ANSWER"), research("first answer"), verification(False)],
            retries=0,
        )

        result = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertEqual(result["verification_retries"], 0)
        self.assertEqual(len(provider.calls), 3)

    def test_maximum_retry_limit_terminates_within_graph_budget(self) -> None:
        responses = [relevance("CAN_ANSWER")]
        for attempt in range(6):
            responses.extend([research(f"answer {attempt}"), verification(False)])
        workflow, provider = self.build_workflow(responses, retries=5)

        result = workflow.full_pipeline("How does DocChat retrieve?", FakeRetriever())

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertEqual(result["verification_retries"], 5)
        self.assertEqual(len(provider.calls), 13)

    def test_out_of_scope_still_terminates_without_research(self) -> None:
        workflow, provider = self.build_workflow([relevance("NO_MATCH")], retries=2)

        result = workflow.full_pipeline("Unrelated question", FakeRetriever())

        self.assertEqual(result["terminal_outcome"], "OUT_OF_SCOPE")
        self.assertEqual(result["verification_retries"], 0)
        self.assertEqual(len(provider.calls), 1)

    def test_retry_limit_configuration_has_a_zero_minimum_and_upper_bound(self) -> None:
        self.assertEqual(Settings(_env_file=None, MAX_VERIFICATION_RETRIES=0).MAX_VERIFICATION_RETRIES, 0)
        with self.assertRaises(ValueError):
            Settings(_env_file=None, MAX_VERIFICATION_RETRIES=-1)
        with self.assertRaises(ValueError):
            Settings(_env_file=None, MAX_VERIFICATION_RETRIES=6)

    def test_retry_limit_accepts_environment_override(self) -> None:
        previous_value = os.environ.get("MAX_VERIFICATION_RETRIES")
        try:
            os.environ["MAX_VERIFICATION_RETRIES"] = "3"
            self.assertEqual(Settings(_env_file=None).MAX_VERIFICATION_RETRIES, 3)
        finally:
            if previous_value is None:
                os.environ.pop("MAX_VERIFICATION_RETRIES", None)
            else:
                os.environ["MAX_VERIFICATION_RETRIES"] = previous_value
