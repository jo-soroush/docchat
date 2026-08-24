"""Focused Hotfix B tests for atomic comparison claim-generation discipline."""

import json
from unittest import TestCase

from langchain.schema import Document

from agents.research_agent import ResearchAgent
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
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return next(self.responses)


class StaticHybridRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def invoke(self, _: str) -> list[Document]:
        return self.documents


def document(document_id: str, chunk_id: str, text: str) -> Document:
    return Document(
        page_content=text,
        metadata={
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source_name": f"{document_id}.pdf",
            "section": f"{document_id} evidence",
        },
    )


def research(answer: str, mappings: dict[str, list[str]]) -> str:
    return json.dumps(
        {
            "draft_answer": answer,
            "claim_sources": [
                {"claim": claim, "chunk_ids": chunk_ids}
                for claim, chunk_ids in mappings.items()
            ],
        }
    )


def verification(*, supported: bool) -> str:
    return json.dumps(
        {
            "supported": supported,
            "relevant": True,
            "unsupported_claims": [] if supported else ["compound claim has an unsupported clause"],
            "contradictions": [],
            "correction_feedback": "" if supported else "Omit the unsupported clause.",
        }
    )


class AtomicComparisonClaimTests(TestCase):
    def setUp(self) -> None:
        self.source_a = document("source-a", "a-1", "Source A supports its own direct fact.")
        self.source_b = document("source-b", "b-1", "Source B supports its own direct fact.")
        self.documents = [self.source_a, self.source_b]

    def retriever(self) -> ActiveDocumentEvidenceRetriever:
        return ActiveDocumentEvidenceRetriever(
            StaticHybridRetriever(self.documents), self.documents, max_chunks=2
        )

    def test_comparison_prompt_requires_atomic_precisely_mapped_claims(self) -> None:
        provider = RecordingProvider([research("Atomic comparison.", {"A": ["a-1"], "B": ["b-1"]})])

        ResearchAgent(provider).generate(
            "Compare the uploaded document sources.",
            self.documents,
            intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        prompt = provider.calls[0]["prompt"]
        self.assertIn("claim-grounding rules", prompt)
        self.assertIn("every factual or comparative claim atomic", prompt)
        self.assertIn("support that precise claim", prompt)
        self.assertIn("map the comparative claim to supporting chunks", prompt)
        self.assertIn("from both sources when both sides are asserted", prompt)
        self.assertIn("external knowledge", prompt)

    def test_atomic_source_claims_resolve_to_their_respective_sources(self) -> None:
        provider = RecordingProvider(
            [research("Atomic source facts.", {"A fact": ["a-1"], "B fact": ["b-1"]})]
        )

        result = ResearchAgent(provider).generate(
            "Compare the uploaded document sources.",
            self.documents,
            intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        self.assertEqual(
            {citation.claim: citation.document_id for citation in result.citations if citation.available},
            {"A fact": "source-a", "B fact": "source-b"},
        )

    def test_true_comparative_claim_can_map_to_evidence_from_both_sources(self) -> None:
        provider = RecordingProvider(
            [research("A differs from B.", {"A differs from B": ["a-1", "b-1"]})]
        )

        result = ResearchAgent(provider).generate(
            "Compare the uploaded document sources.",
            self.documents,
            intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        self.assertEqual(
            {citation.document_id for citation in result.citations if citation.available},
            {"source-a", "source-b"},
        )

    def test_compound_claim_with_unsupported_clause_still_cannot_be_verified(self) -> None:
        provider = RecordingProvider(
            [
                research(
                    "A and B make a compound claim with one unsupported clause.",
                    {"compound claim": ["a-1", "b-1"]},
                ),
                verification(supported=False),
            ]
        )
        workflow = AgentWorkflow(provider, Settings(_env_file=None, MAX_VERIFICATION_RETRIES=0))

        result = workflow.full_pipeline(
            "Compare the uploaded document sources.",
            self.retriever(),
            evidence_intent=EvidenceIntent.MULTI_DOCUMENT_COMPARISON,
        )

        self.assertEqual(len(result["comparison_grounding"]["grounded_source_ids"]), 2)
        self.assertEqual(result["terminal_outcome"], "RETRY_EXHAUSTED")
        self.assertFalse(result["verification_result"]["supported"])

    def test_question_and_synthesis_prompts_do_not_receive_comparison_rules(self) -> None:
        for intent in (EvidenceIntent.QUESTION, EvidenceIntent.DOCUMENT_SYNTHESIS):
            with self.subTest(intent=intent):
                provider = RecordingProvider([research("Grounded answer.", {"fact": ["a-1"]})])
                ResearchAgent(provider).generate("Answer.", [self.source_a], intent=intent)
                self.assertNotIn("claim-grounding rules", provider.calls[0]["prompt"])
