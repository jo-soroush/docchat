"""Focused maintenance tests for question-aware verification semantics."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.contracts import StructuredOutputError, VerificationResult
from agents.verification_agent import VerificationAgent
from agents.workflow import AgentWorkflow
from config.settings import Settings


class RecordingProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def generate_structured(
        self, prompt: str, *, schema: dict, temperature: float, max_tokens: int
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return next(self.responses)


class StaticRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def relevance() -> str:
    return json.dumps({"decision": "CAN_ANSWER", "explanation": "evidence available"})


def research(answer: str) -> str:
    return json.dumps({"draft_answer": answer, "claim_sources": []})


def verification(
    *, supported: bool, relevant: bool, unsupported_claims: list[str] | None = None,
    contradictions: list[str] | None = None, feedback: str = ""
) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": relevant,
            "unsupported_claims": unsupported_claims or [],
            "contradictions": contradictions or [],
            "correction_feedback": feedback,
        }
    )


class VerificationSemanticsTests(TestCase):
    question = "According to the document, what are the three stages of the agent loop?"
    answer = "The three stages of the agent loop are perceive, reason, and act."
    evidence = [
        Document(
            page_content="The three stages of the agent loop are perceive, reason, and act.",
            metadata={"document_id": "agent-loop", "chunk_id": "key-takeaways"},
        ),
        Document(page_content="Related agent material may contain additional information."),
    ]

    def test_scoped_supported_answer_receives_question_and_semantic_guardrails(self) -> None:
        provider = RecordingProvider([verification(supported=True, relevant=True)])

        result = VerificationAgent(provider).check(self.question, self.answer, self.evidence)

        self.assertFalse(result.requires_research)
        prompt = provider.calls[0]["prompt"]
        self.assertIn(f"Question: {self.question}", prompt)
        self.assertIn("Do not use external or model knowledge.", prompt)
        self.assertIn("Do not penalize a scoped answer", prompt)
        self.assertIn("only conflicts between the answer and the supplied evidence", prompt)

    def test_supported_and_relevant_result_routes_to_verified(self) -> None:
        provider = RecordingProvider(
            [relevance(), research(self.answer), verification(supported=True, relevant=True)]
        )

        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            self.question, StaticRetriever(self.evidence)
        )

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual(result["verification_retries"], 0)
        self.assertIn(f"Question: {self.question}", provider.calls[2]["prompt"])

    def test_genuinely_unsupported_answer_still_requires_research(self) -> None:
        provider = RecordingProvider(
            [verification(supported=False, relevant=True, unsupported_claims=["unsupported claim"])]
        )

        result = VerificationAgent(provider).check(self.question, "Unsupported answer.", self.evidence)

        self.assertTrue(result.requires_research)

    def test_genuinely_irrelevant_answer_still_requires_research(self) -> None:
        provider = RecordingProvider([verification(supported=True, relevant=False)])

        result = VerificationAgent(provider).check(self.question, "A supported but unrelated answer.", self.evidence)

        self.assertTrue(result.requires_research)

    def test_supported_result_cannot_claim_evidence_failures(self) -> None:
        invalid = verification(
            supported=True,
            relevant=True,
            contradictions=["Unsupported external requirement"],
        )

        with self.assertRaises(StructuredOutputError):
            VerificationResult.from_model_json(invalid)

    def test_prompt_forbids_external_corrections_not_grounded_in_evidence(self) -> None:
        provider = RecordingProvider([verification(supported=True, relevant=True)])

        VerificationAgent(provider).check(self.question, self.answer, self.evidence)

        prompt = provider.calls[0]["prompt"]
        self.assertIn("list only conflicts between the answer and the supplied evidence", prompt)
        self.assertIn("list only claims made by the answer that lack support", prompt)
