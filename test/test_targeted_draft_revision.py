"""Focused Hotfix B tests for targeted draft revision within C03's retry budget."""

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


class TargetedDraftRevisionTests(TestCase):
    def setUp(self) -> None:
        self.source_a = document("source-a", "a-1")
        self.source_b = document("source-b", "b-1")
        self.question_documents = [self.source_a]
        self.comparison_documents = [self.source_a, self.source_b]

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

    def test_first_attempt_has_no_previous_draft_and_each_retry_uses_latest_draft_and_feedback(self) -> None:
        feedback_one = "Remove claim one."
        feedback_two = "Remove claim two."
        provider = RecordingProvider(
            [
                relevance(),
                research("first draft", {"A": ["a-1"]}),
                verification(supported=False, feedback=feedback_one),
                research("second draft", {"A": ["a-1"]}),
                verification(supported=False, feedback=feedback_two),
                research("third draft", {"A": ["a-1"]}),
                verification(supported=False, feedback="final"),
            ]
        )

        result = self.workflow(provider).full_pipeline("Question", self.retriever(self.question_documents))
        prompts = self.research_prompts(provider)

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertNotIn("Previous draft answer", prompts[0])
        self.assertIn("first draft", prompts[1])
        self.assertIn(feedback_one, prompts[1])
        self.assertNotIn("second draft", prompts[1])
        self.assertIn("second draft", prompts[2])
        self.assertIn(feedback_two, prompts[2])
        self.assertNotIn("first draft", prompts[2])

    def test_targeted_revision_preserves_supported_content_and_revises_only_flagged_claim(self) -> None:
        feedback = "Remove the unsupported detail."
        provider = RecordingProvider(
            [
                relevance(),
                research("Supported fact. Unsupported detail.", {"fact": ["a-1"]}),
                verification(supported=False, feedback=feedback),
                research("Supported fact.", {"fact": ["a-1"]}),
                verification(supported=True),
            ]
        )

        result = self.workflow(provider, retries=1).full_pipeline(
            "Question", self.retriever(self.question_documents)
        )
        retry_prompt = self.research_prompts(provider)[1]

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(result["draft_answer"], "Supported fact.")
        self.assertIn("Supported fact. Unsupported detail.", retry_prompt)
        self.assertIn(feedback, retry_prompt)
        self.assertIn("Preserve content", retry_prompt)

    def test_revised_comparison_still_requires_current_draft_grounding_and_verification(self) -> None:
        feedback = "Ground the comparison in both sources."
        provider = RecordingProvider(
            [
                research("first comparison", {"A": ["a-1"], "B": ["b-1"]}),
                verification(supported=False, feedback=feedback),
                research("revised one-source comparison", {"A only": ["a-1"]}),
            ]
        )

        result = self.workflow(provider, retries=1).full_pipeline(
            "Compare sources.",
            self.retriever(self.comparison_documents),
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        self.assertIn("first comparison", self.research_prompts(provider)[1])
        self.assertIn("claim-grounding rules", self.research_prompts(provider)[1])
        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertIsNone(result["verification_result"])
        self.assertEqual(result["comparison_grounding"]["missing_source_ids"], ["source-b"])

    def test_failed_revision_cannot_become_verified_and_remains_bounded(self) -> None:
        provider = RecordingProvider(
            [
                relevance(),
                research("first", {"A": ["a-1"]}),
                verification(supported=False, feedback="Revise one."),
                research("second", {"A": ["a-1"]}),
                verification(supported=False, feedback="Revise two."),
            ]
        )

        result = self.workflow(provider, retries=1).full_pipeline(
            "Question", self.retriever(self.question_documents)
        )

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertFalse(result["verification_result"]["supported"])
        self.assertEqual(result["verification_retries"], 1)

    def test_question_and_synthesis_remain_compatible_with_targeted_revision(self) -> None:
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
                retry_prompt = self.research_prompts(provider)[1]

                self.assertEqual(result["terminal_outcome"], "VERIFIED")
                self.assertIn("Previous draft answer: first", retry_prompt)
                self.assertNotIn("claim-grounding rules", retry_prompt)
