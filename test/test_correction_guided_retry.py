"""Focused Hotfix B tests for bounded, typed correction-guided re-research."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.workflow import AgentWorkflow
from config.settings import Settings
from retriever.evidence import ActiveDocumentEvidenceRetriever, EvidenceIntent


class RecordingProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def generate_structured(
        self, prompt: str, *, schema: dict, temperature: float, max_tokens: int
    ) -> str:
        self.calls.append({"prompt": prompt, "schema": schema})
        return next(self.responses)


class StaticHybridRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def document(document_id: str, chunk_id: str) -> Document:
    return Document(
        page_content=f"Evidence for {document_id}.",
        metadata={
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source_name": f"{document_id}.pdf",
            "section": f"{document_id} section",
        },
    )


def relevance() -> str:
    return json.dumps({"decision": "CAN_ANSWER", "explanation": "fixture evidence"})


def research(answer: str, claims: dict[str, list[str]]) -> str:
    return json.dumps(
        {
            "draft_answer": answer,
            "claim_sources": [
                {"claim": claim, "chunk_ids": chunk_ids} for claim, chunk_ids in claims.items()
            ],
        }
    )


def verification(*, supported: bool, feedback: str = "") -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": True,
            "unsupported_claims": [] if supported else ["unsupported fixture claim"],
            "contradictions": [],
            "correction_feedback": feedback,
        }
    )


class CorrectionGuidedRetryTests(TestCase):
    def setUp(self) -> None:
        self.source_a = document("source-a", "a-1")
        self.source_b = document("source-b", "b-1")
        self.comparison_documents = [self.source_a, self.source_b]
        self.question_documents = [self.source_a]

    @staticmethod
    def workflow(provider: RecordingProvider, retries: int = 2) -> AgentWorkflow:
        return AgentWorkflow(provider, Settings(_env_file=None, MAX_VERIFICATION_RETRIES=retries))

    @staticmethod
    def retriever(documents: list[Document]) -> ActiveDocumentEvidenceRetriever:
        return ActiveDocumentEvidenceRetriever(StaticHybridRetriever(documents), documents, max_chunks=4)

    @staticmethod
    def research_prompts(provider: RecordingProvider) -> list[str]:
        return [
            call["prompt"]
            for call in provider.calls
            if '"draft_answer"' in json.dumps(call["schema"])
        ]

    def test_first_attempt_has_no_feedback_and_retries_use_only_immediately_prior_feedback(self) -> None:
        first_feedback = "Remove the first unsupported clause."
        second_feedback = "Remove the second unsupported clause."
        provider = RecordingProvider(
            [
                relevance(),
                research("first", {"A": ["a-1"]}),
                verification(supported=False, feedback=first_feedback),
                research("second", {"A": ["a-1"]}),
                verification(supported=False, feedback=second_feedback),
                research("third", {"A": ["a-1"]}),
                verification(supported=False, feedback="final"),
            ]
        )

        result = self.workflow(provider).full_pipeline("Question", self.retriever(self.question_documents))
        prompts = self.research_prompts(provider)

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertEqual(len(prompts), 3)
        self.assertNotIn("Verifier correction feedback", prompts[0])
        self.assertIn(first_feedback, prompts[1])
        self.assertNotIn(second_feedback, prompts[1])
        self.assertIn(second_feedback, prompts[2])
        self.assertNotIn(first_feedback, prompts[2])

    def test_supported_result_stops_without_extra_research_or_feedback(self) -> None:
        provider = RecordingProvider(
            [relevance(), research("grounded", {"A": ["a-1"]}), verification(supported=True)]
        )

        result = self.workflow(provider).full_pipeline("Question", self.retriever(self.question_documents))

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(result["verification_retries"], 0)
        self.assertEqual(len(self.research_prompts(provider)), 1)

    def test_feedback_cannot_bypass_verification_and_retry_remains_bounded(self) -> None:
        provider = RecordingProvider(
            [
                relevance(),
                research("first", {"A": ["a-1"]}),
                verification(supported=False, feedback="Correct it."),
                research("revised", {"A": ["a-1"]}),
                verification(supported=False, feedback="Correct it again."),
            ]
        )

        result = self.workflow(provider, retries=1).full_pipeline(
            "Question", self.retriever(self.question_documents)
        )

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertFalse(result["verification_result"]["supported"])
        self.assertEqual(result["verification_retries"], 1)
        self.assertEqual(len(self.research_prompts(provider)), 2)

    def test_corrected_comparison_still_requires_current_draft_source_grounding(self) -> None:
        feedback = "Use supported comparison claims from both sources."
        provider = RecordingProvider(
            [
                research("first comparison", {"A": ["a-1"], "B": ["b-1"]}),
                verification(supported=False, feedback=feedback),
                research("one-source revision", {"A only": ["a-1"]}),
            ]
        )

        result = self.workflow(provider, retries=1).full_pipeline(
            "Compare the uploaded sources.",
            self.retriever(self.comparison_documents),
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )
        retry_prompt = self.research_prompts(provider)[1]

        self.assertIn(feedback, retry_prompt)
        self.assertIn("claim-grounding rules", retry_prompt)
        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertIsNone(result["verification_result"])
        self.assertEqual(result["comparison_grounding"]["missing_source_ids"], ["source-b"])

    def test_question_and_synthesis_retry_prompts_preserve_their_existing_intents(self) -> None:
        for intent, documents in (
            (EvidenceIntent.QUESTION, self.question_documents),
            (EvidenceIntent.DOCUMENT_SYNTHESIS, self.question_documents),
        ):
            with self.subTest(intent=intent):
                provider = RecordingProvider(
                    [
                        relevance() if intent is EvidenceIntent.QUESTION else research("first", {"A": ["a-1"]}),
                        research("first", {"A": ["a-1"]}) if intent is EvidenceIntent.QUESTION else verification(supported=False, feedback="Revise."),
                        verification(supported=False, feedback="Revise.") if intent is EvidenceIntent.QUESTION else research("second", {"A": ["a-1"]}),
                        research("second", {"A": ["a-1"]}) if intent is EvidenceIntent.QUESTION else verification(supported=True),
                        verification(supported=True) if intent is EvidenceIntent.QUESTION else "",
                    ]
                )
                result = self.workflow(provider, retries=1).full_pipeline(
                    "Question" if intent is EvidenceIntent.QUESTION else "Summarize.",
                    self.retriever(documents),
                    evidence_intent=intent,
                )
                prompts = self.research_prompts(provider)

                self.assertEqual(result["terminal_outcome"], "VERIFIED")
                self.assertIn("Revise.", prompts[1])
                self.assertNotIn("claim-grounding rules", prompts[1])

    def test_trace_records_feedback_presence_without_feedback_content(self) -> None:
        secret_feedback = "private correction content must not be traced"
        provider = RecordingProvider(
            [
                relevance(),
                research("first", {"A": ["a-1"]}),
                verification(supported=False, feedback=secret_feedback),
                research("second", {"A": ["a-1"]}),
                verification(supported=True),
            ]
        )

        result = self.workflow(provider, retries=1).full_pipeline(
            "Question", self.retriever(self.question_documents)
        )
        trace = result["run_trace"]
        routing_event = next(event for event in trace["events"] if event["stage"] == "ROUTING")
        research_events = [event for event in trace["events"] if event["stage"] == "RESEARCH"]

        self.assertTrue(routing_event["correction_feedback_supplied"])
        self.assertEqual([event["correction_feedback_supplied"] for event in research_events], [False, True])
        self.assertNotIn(secret_feedback, json.dumps(trace))
