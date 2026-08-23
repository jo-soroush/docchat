"""Focused maintenance tests for bounded Ollama verification output."""

import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from langchain.schema import Document

from agents.contracts import RelevanceResult, ResearchResult, StructuredOutputError, VerificationResult
from agents.relevance_checker import RelevanceChecker
from agents.research_agent import ResearchAgent
from agents.verification_agent import VerificationAgent
from providers.ollama import OllamaChatProvider, OllamaProviderError


class RecordingStructuredProvider:
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


def verification_json() -> str:
    return json.dumps(
        {
            "supported": True,
            "relevant": True,
            "unsupported_claims": [],
            "contradictions": [],
            "correction_feedback": "",
        }
    )


class VerificationOutputTests(TestCase):
    def test_verification_uses_a_bounded_300_token_structured_request(self) -> None:
        provider = RecordingStructuredProvider([verification_json()])
        result = VerificationAgent(provider).check(
            "What is the grounded answer?",
            "A grounded answer.",
            [Document(page_content="Grounding evidence.")],
        )

        self.assertTrue(result.supported)
        self.assertEqual(provider.calls[0]["schema"], VerificationResult.model_json_schema())
        self.assertEqual(provider.calls[0]["temperature"], 0.0)
        self.assertEqual(provider.calls[0]["max_tokens"], 300)

    def test_complete_verification_json_validates_normally(self) -> None:
        result = VerificationResult.from_model_json(verification_json())

        self.assertTrue(result.supported)
        self.assertFalse(result.requires_research)

    def test_malformed_verification_json_remains_strictly_rejected(self) -> None:
        provider = RecordingStructuredProvider(['{"supported": true'])

        with self.assertRaises(StructuredOutputError):
            VerificationAgent(provider).check(
                "Question", "Answer", [Document(page_content="Evidence")]
            )

    @patch("providers.ollama.ChatOllama")
    def test_length_stopped_structured_response_is_safe_provider_failure(
        self, chat_class: Mock
    ) -> None:
        raw_truncated_content = '{"supported": false, "unsupported_claims": ['
        chat_class.return_value.bind.return_value.invoke.return_value = SimpleNamespace(
            content=raw_truncated_content,
            response_metadata={"done_reason": "length"},
        )
        provider = OllamaChatProvider(model="chat-test", base_url="http://ollama.test:11434")

        with self.assertRaisesRegex(
            OllamaProviderError, "exceeded its generation limit"
        ) as error:
            provider.generate_structured(
                "prompt", schema=VerificationResult.model_json_schema(), temperature=0, max_tokens=300
            )

        self.assertNotIn(raw_truncated_content, str(error.exception))

    def test_relevance_and_research_budgets_remain_unchanged(self) -> None:
        documents = [
            Document(
                page_content="Grounding evidence.",
                metadata={"document_id": "document", "chunk_id": "chunk"},
            )
        ]
        provider = RecordingStructuredProvider(
            [
                json.dumps({"decision": "CAN_ANSWER", "explanation": "grounded"}),
                json.dumps({"draft_answer": "Grounded answer.", "claim_sources": []}),
            ]
        )

        relevance = RelevanceChecker(provider).check("Question", StaticRetriever(documents))
        research = ResearchAgent(provider).generate("Question", documents)

        self.assertTrue(relevance.is_relevant)
        self.assertEqual(research.draft_answer, "Grounded answer.")
        self.assertEqual(
            [(call["schema"], call["max_tokens"]) for call in provider.calls],
            [
                (RelevanceResult.model_json_schema(), 100),
                (ResearchResult.model_json_schema(), 300),
            ],
        )
