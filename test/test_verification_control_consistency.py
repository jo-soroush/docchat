"""Focused tests for strict VerificationResult control-state consistency."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.contracts import (
    StructuredOutputError,
    SupportedVerificationResult,
    UnsupportedVerificationResult,
    VerificationResult,
)
from agents.verification_agent import VerificationAgent
from agents.workflow import AgentWorkflow
from config.settings import Settings
from retriever.evidence import EvidenceIntent


class RecordingProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompt = ""

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        self.prompt = prompt
        return self.response


class SequencedProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)

    def generate_structured(self, prompt: str, *, schema: dict, temperature: float, max_tokens: int) -> str:
        del prompt, schema, temperature, max_tokens
        return next(self.responses)


class StaticRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def result_json(
    *,
    supported: bool,
    relevant: bool = True,
    unsupported_claims: list[str] | None = None,
    contradictions: list[str] | None = None,
    feedback: str = "",
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


class VerificationControlConsistencyTests(TestCase):
    def test_supported_and_unsupported_variants_parse_as_distinct_types(self) -> None:
        supported = VerificationResult.from_model_json(result_json(supported=True))
        unsupported = VerificationResult.from_model_json(
            result_json(supported=False, unsupported_claims=["unsupported claim"])
        )

        self.assertIsInstance(supported, SupportedVerificationResult)
        self.assertIsInstance(unsupported, UnsupportedVerificationResult)

    def test_provider_schema_exposes_mutually_exclusive_supported_states(self) -> None:
        schema = VerificationResult.model_json_schema()
        self.assertIn("oneOf", schema)
        self.assertEqual(schema["discriminator"]["propertyName"], "supported")

        supported_schema = schema["$defs"]["SupportedVerificationResult"]
        self.assertIs(supported_schema["properties"]["supported"]["const"], True)
        self.assertEqual(supported_schema["properties"]["unsupported_claims"]["maxItems"], 0)
        self.assertEqual(supported_schema["properties"]["contradictions"]["maxItems"], 0)

    def test_supported_result_requires_empty_unsupported_claims(self) -> None:
        with self.assertRaises(StructuredOutputError):
            VerificationResult.from_model_json(
                result_json(supported=True, unsupported_claims=["unsupported claim"])
            )

    def test_supported_result_requires_empty_contradictions(self) -> None:
        with self.assertRaises(StructuredOutputError):
            VerificationResult.from_model_json(
                result_json(supported=True, contradictions=["evidence contradiction"])
            )

    def test_unsupported_claims_pass_only_with_supported_false(self) -> None:
        result = VerificationResult.from_model_json(
            result_json(supported=False, unsupported_claims=["unsupported claim"])
        )

        self.assertFalse(result.supported)
        self.assertTrue(result.requires_research)

    def test_contradictions_pass_only_with_supported_false(self) -> None:
        result = VerificationResult.from_model_json(
            result_json(supported=False, contradictions=["evidence contradiction"])
        )

        self.assertFalse(result.supported)
        self.assertTrue(result.requires_research)

    def test_valid_supported_synthesis_result_passes_strict_validation(self) -> None:
        provider = RecordingProvider(result_json(supported=True))

        result = VerificationAgent(provider).check(
            "Summarize the uploaded document(s).",
            "A grounded synthesis.",
            [Document(page_content="Grounded synthesis evidence.")],
            intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
        )

        self.assertTrue(result.supported)
        self.assertFalse(result.requires_research)
        self.assertIn("control-state consistency rules", provider.prompt)
        self.assertIn("unsupported_claims MUST be []", provider.prompt)
        self.assertIn("lack support", provider.prompt)

    def test_valid_unsupported_synthesis_result_passes_strict_validation(self) -> None:
        provider = RecordingProvider(
            result_json(
                supported=False,
                unsupported_claims=["claim absent from supplied evidence"],
                feedback="Remove the unsupported claim.",
            )
        )

        result = VerificationAgent(provider).check(
            "Summarize the uploaded document(s).",
            "An unsupported synthesis.",
            [Document(page_content="Different evidence.")],
            intent=EvidenceIntent.DOCUMENT_SYNTHESIS,
        )

        self.assertFalse(result.supported)
        self.assertTrue(result.requires_research)

    def test_contradictory_verification_output_cannot_route_to_verified(self) -> None:
        provider = SequencedProvider(
            [
                json.dumps({"decision": "CAN_ANSWER", "explanation": "evidence exists"}),
                json.dumps({"draft_answer": "Grounded answer.", "claim_sources": []}),
                result_json(supported=True, unsupported_claims=["contradictory control state"]),
            ]
        )
        workflow = AgentWorkflow(provider, Settings(_env_file=None))

        result = workflow.full_pipeline(
            "What does the document say?",
            StaticRetriever([Document(page_content="Grounded evidence.")]),
        )

        self.assertEqual(result["terminal_outcome"], "FAILURE")
        self.assertIsNone(result["verification_result"])
        self.assertIn("malformed structured output", result["verification_report"])
