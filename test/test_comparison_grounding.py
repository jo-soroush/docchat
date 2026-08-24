"""Focused Hotfix B tests for current-draft multi-source comparison grounding."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.citations import evaluate_comparison_grounding, resolve_claim_sources
from agents.contracts import ClaimSource
from agents.workflow import AgentWorkflow
from config.settings import Settings
from retriever.evidence import ActiveDocumentEvidenceRetriever, EvidenceIntent


class StaticHybridRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


class SequencedProvider:
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


def document(document_id: str, chunk_id: str) -> Document:
    return Document(
        page_content=f"Evidence for {document_id} in {chunk_id}.",
        metadata={
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source_name": f"{document_id}.pdf",
            "section": f"{document_id} section",
        },
    )


def research(claim_sources: dict[str, list[str]]) -> str:
    return json.dumps(
        {
            "draft_answer": "A comparison draft.",
            "claim_sources": [
                {"claim": claim, "chunk_ids": chunk_ids}
                for claim, chunk_ids in claim_sources.items()
            ],
        }
    )


def verification(*, supported: bool, relevant: bool = True) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": relevant,
            "unsupported_claims": [] if supported else ["unsupported comparison claim"],
            "contradictions": [],
            "correction_feedback": "" if supported else "Use supported comparison claims.",
        }
    )


class ComparisonGroundingTests(TestCase):
    def setUp(self) -> None:
        self.source_a = [document("source-a", "a-1"), document("source-a", "a-2")]
        self.source_b = [document("source-b", "b-1"), document("source-b", "b-2")]
        self.source_c = [document("source-c", "c-1")]
        self.documents = [*self.source_a, *self.source_b]

    def citations_for(self, mappings: dict[str, list[str]], documents: list[Document] | None = None):
        return resolve_claim_sources(
            [ClaimSource(claim=claim, chunk_ids=chunk_ids) for claim, chunk_ids in mappings.items()],
            documents or self.documents,
        )

    def comparison_retriever(self, documents: list[Document] | None = None):
        active_documents = documents or self.documents
        return ActiveDocumentEvidenceRetriever(
            StaticHybridRetriever(active_documents), active_documents, max_chunks=4
        )

    def test_two_source_valid_mappings_pass_and_unknown_ids_do_not_count(self) -> None:
        citations = self.citations_for({"A": ["a-1"], "B": ["b-1"], "unknown": ["missing"]})

        grounding = evaluate_comparison_grounding(citations, self.documents)

        self.assertTrue(grounding.is_complete)
        self.assertEqual(grounding.active_source_ids, ["source-a", "source-b"])
        self.assertEqual(grounding.grounded_source_ids, ["source-a", "source-b"])
        self.assertEqual(grounding.missing_source_ids, [])
        self.assertFalse(citations[-1].available)

    def test_each_single_source_mapping_fails_two_source_grounding(self) -> None:
        for mapping, expected_missing in (
            ({"A": ["a-1"]}, ["source-b"]),
            ({"B": ["b-1"]}, ["source-a"]),
        ):
            with self.subTest(mapping=mapping):
                grounding = evaluate_comparison_grounding(self.citations_for(mapping), self.documents)
                self.assertFalse(grounding.is_complete)
                self.assertEqual(grounding.missing_source_ids, expected_missing)

    def test_all_active_sources_are_required_for_n_source_comparison(self) -> None:
        documents = [*self.documents, *self.source_c]
        grounding = evaluate_comparison_grounding(
            self.citations_for({"A": ["a-1"], "B": ["b-1"]}, documents), documents
        )

        self.assertEqual(grounding.active_source_count, 3)
        self.assertEqual(grounding.grounded_source_count, 2)
        self.assertEqual(grounding.missing_source_ids, ["source-c"])

    def test_incomplete_comparison_never_reaches_verification_or_verified(self) -> None:
        provider = SequencedProvider([research({"A only": ["a-1"]})])
        workflow = AgentWorkflow(provider, Settings(_env_file=None, MAX_VERIFICATION_RETRIES=0))

        result = workflow.full_pipeline(
            "Compare the uploaded document sources.",
            self.comparison_retriever(),
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertIsNone(result["verification_result"])
        self.assertEqual(result["citations"], [])
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(result["comparison_grounding"]["missing_source_ids"], ["source-b"])
        research_event = next(event for event in result["run_trace"]["events"] if event["stage"] == "RESEARCH")
        self.assertEqual(research_event["active_source_count"], 2)
        self.assertEqual(research_event["grounded_source_count"], 1)
        self.assertEqual(research_event["missing_source_ids"], ["source-b"])

    def test_later_one_source_draft_cannot_reuse_prior_citations_or_verification(self) -> None:
        provider = SequencedProvider(
            [
                research({"A": ["a-1"], "B": ["b-1"]}),
                verification(supported=False),
                research({"A only": ["a-2"]}),
            ]
        )
        workflow = AgentWorkflow(provider, Settings(_env_file=None, MAX_VERIFICATION_RETRIES=1))

        result = workflow.full_pipeline(
            "Compare the uploaded document sources.",
            self.comparison_retriever(),
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertEqual(result["citations"], [])
        self.assertIsNone(result["verification_result"])
        self.assertEqual(result["comparison_grounding"]["grounded_source_ids"], ["source-a"])
        self.assertEqual(result["comparison_grounding"]["missing_source_ids"], ["source-b"])
        self.assertEqual(len(provider.calls), 3)

    def test_complete_comparison_still_requires_verification(self) -> None:
        provider = SequencedProvider(
            [research({"A": ["a-1"], "B": ["b-1"]}), verification(supported=True)]
        )
        result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
            "Compare the uploaded document sources.",
            self.comparison_retriever(),
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        self.assertEqual(result["terminal_outcome"], "VERIFIED")
        self.assertEqual({item["document_id"] for item in result["citations"]}, {"source-a", "source-b"})
        self.assertTrue(result["comparison_grounding"]["missing_source_ids"] == [])
        self.assertEqual(len(provider.calls), 2)

    def test_question_and_document_synthesis_do_not_receive_comparison_grounding(self) -> None:
        for intent, documents in (
            (EvidenceIntent.QUESTION, self.source_a),
            (EvidenceIntent.DOCUMENT_SYNTHESIS, self.source_a),
        ):
            with self.subTest(intent=intent):
                provider = SequencedProvider(
                    [
                        json.dumps({"decision": "CAN_ANSWER", "explanation": "evidence"})
                        if intent is EvidenceIntent.QUESTION
                        else research({"A": ["a-1"]}),
                        research({"A": ["a-1"]}) if intent is EvidenceIntent.QUESTION else verification(supported=True),
                        verification(supported=True) if intent is EvidenceIntent.QUESTION else "",
                    ]
                )
                retriever = self.comparison_retriever(documents)
                result = AgentWorkflow(provider, Settings(_env_file=None)).full_pipeline(
                    "What does source A say?" if intent is EvidenceIntent.QUESTION else "Summarize.",
                    retriever,
                    evidence_intent=intent,
                )
                self.assertEqual(result["terminal_outcome"], "VERIFIED")
                self.assertIsNone(result["comparison_grounding"])
