"""Focused V1-C08 tests for safe, typed workflow run traces."""

import json
from unittest import TestCase
from uuid import UUID

from langchain.schema import Document

from agents.workflow import AgentWorkflow
from config.settings import Settings


class FakeChatProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)

    def generate(self, prompt: str, *, temperature: float, max_tokens: int) -> str:
        del prompt, temperature, max_tokens
        return next(self.responses)

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        del schema
        return self.generate(prompt, temperature=temperature, max_tokens=max_tokens)


class FakeRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def relevance(decision: str) -> str:
    return json.dumps({"decision": decision, "explanation": "fixture relevance"})


def research(answer: str) -> str:
    return json.dumps({"draft_answer": answer})


def verification(supported: bool) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": True,
            "unsupported_claims": [] if supported else ["fixture unsupported claim"],
            "contradictions": [],
            "correction_feedback": "fixture correction",
        }
    )


class RunTraceTests(TestCase):
    def workflow(self, responses: list[str], retries: int = 2) -> AgentWorkflow:
        return AgentWorkflow(
            FakeChatProvider(responses), Settings(_env_file=None, MAX_VERIFICATION_RETRIES=retries)
        )

    @staticmethod
    def retriever() -> FakeRetriever:
        return FakeRetriever(
            [
                Document(
                    page_content="private document content must never appear in a trace",
                    metadata={"chunk_id": "safe-chunk-id", "document_id": "safe-document-id"},
                )
            ]
        )

    def test_verified_trace_records_ids_typed_decisions_route_and_terminal_outcome(self) -> None:
        result = self.workflow(
            [relevance("CAN_ANSWER"), research("grounded answer"), verification(True)]
        ).full_pipeline("private question", self.retriever())

        trace = result["run_trace"]
        UUID(hex=trace["run_id"])
        self.assertGreaterEqual(trace["duration_ms"], 0)
        self.assertTrue(all(event["stage_latency_ms"] >= 0 for event in trace["events"]))
        self.assertEqual(trace["events"][0]["stage"], "RETRIEVAL")
        self.assertEqual(trace["events"][0]["retrieved_chunk_ids"], ["safe-chunk-id"])
        relevance_event = next(event for event in trace["events"] if event["stage"] == "RELEVANCE")
        verification_event = next(event for event in trace["events"] if event["stage"] == "VERIFICATION")
        terminal_event = trace["events"][-1]
        self.assertEqual((relevance_event["relevance_decision"], relevance_event["route"]), ("CAN_ANSWER", "relevant"))
        self.assertEqual((verification_event["verification_supported"], verification_event["route"]), (True, "verified"))
        self.assertEqual((terminal_event["stage"], terminal_event["terminal_outcome"]), ("TERMINAL", "VERIFIED"))

    def test_retry_trace_records_attempts_routes_and_retry_exhaustion(self) -> None:
        result = self.workflow(
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
        ).full_pipeline("question", self.retriever())

        trace = result["run_trace"]
        verification_events = [event for event in trace["events"] if event["stage"] == "VERIFICATION"]
        routing_events = [event for event in trace["events"] if event["stage"] == "ROUTING"]
        self.assertEqual([event["route"] for event in verification_events], ["re_research", "re_research", "retry_exhausted"])
        self.assertEqual([event["attempt"] for event in routing_events], [1, 2])
        self.assertEqual(trace["events"][-1]["terminal_outcome"], "RETRY_EXHAUSTED")

    def test_out_of_scope_trace_localizes_relevance_without_research_or_verification(self) -> None:
        result = self.workflow([relevance("NO_MATCH")]).full_pipeline("outside question", self.retriever())

        stages = [event["stage"] for event in result["run_trace"]["events"]]
        self.assertEqual(stages, ["RETRIEVAL", "RELEVANCE", "TERMINAL"])
        self.assertEqual(result["run_trace"]["events"][-1]["terminal_outcome"], "OUT_OF_SCOPE")

    def test_malformed_output_trace_records_only_safe_error_without_raw_content(self) -> None:
        result = self.workflow([relevance("CAN_ANSWER"), research("answer"), "not valid JSON"]).full_pipeline(
            "private question", self.retriever()
        )

        serialized_trace = json.dumps(result["run_trace"])
        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertIn("The verification model returned malformed structured output.", serialized_trace)
        self.assertNotIn("not valid JSON", serialized_trace)
        self.assertNotIn("private question", serialized_trace)
        self.assertNotIn("private document content", serialized_trace)
