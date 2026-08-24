"""Research answer generation behind a typed model-output contract."""

from langchain.schema import Document

from providers.contracts import ChatProvider
from retriever.evidence import EvidenceIntent

from .citations import build_citation_context, resolve_claim_sources
from .contracts import ResearchResult


class ResearchAgent:
    def __init__(self, model: ChatProvider):
        self.model = model

    def generate_prompt(
        self,
        question: str,
        context: str,
        intent: EvidenceIntent,
        correction_feedback: str | None = None,
        previous_draft: str | None = None,
    ) -> str:
        return f"""
You are an AI assistant designed to provide precise factual answers from the given context.

Answer the question using only the context. Return ONLY a JSON object with this exact schema:
{{"draft_answer":"clear concise answer","claim_sources":[{{"claim":"important factual claim","chunk_ids":["chunk ID from context"]}}]}}

For every important factual claim, include only chunk IDs shown in the context. If no source can be mapped, return an empty claim_sources array. Do not invent IDs.
{self._intent_instructions(intent)}
{self._retry_instructions(previous_draft, correction_feedback)}

Question: {question}
Context: {context}
"""

    def generate(
        self,
        question: str,
        documents: list[Document],
        intent: EvidenceIntent = EvidenceIntent.QUESTION,
        correction_feedback: str | None = None,
        previous_draft: str | None = None,
    ) -> ResearchResult:
        context = build_citation_context(documents)
        response_text = self.model.generate_structured(
            self.generate_prompt(question, context, intent, correction_feedback, previous_draft),
            schema=ResearchResult.model_json_schema(),
            temperature=0.3,
            max_tokens=1500,
        )
        result = ResearchResult.from_model_json(response_text)
        return result.model_copy(
            update={"citations": resolve_claim_sources(result.claim_sources, documents)}
        )

    @staticmethod
    def _intent_instructions(intent: EvidenceIntent) -> str:
        """Add task-specific generation discipline without changing core contracts."""
        if intent is not EvidenceIntent.MULTI_DOCUMENT_COMPARISON:
            return ""
        return """

For MULTI_DOCUMENT_COMPARISON, apply these claim-grounding rules:
- Make every factual or comparative claim atomic: do not bundle independently
  verifiable facts into one claim.
- Every factual clause must be supported by the supplied selected evidence. Omit
  any detail whose support is insufficient; never infer from external knowledge.
- Attach each claim_source only to chunks that support that precise claim.
- For a similarity or difference between sources, ensure the source-A side is
  supported by selected source-A evidence and the source-B side is supported by
  selected source-B evidence; map the comparative claim to supporting chunks
  from both sources when both sides are asserted.
- Do not let a source name, document identity, or one source's evidence stand in
  for factual support from another source.
"""

    @staticmethod
    def _retry_instructions(
        previous_draft: str | None, correction_feedback: str | None
    ) -> str:
        """Revise only the immediately preceding draft during one bounded retry."""
        if previous_draft is None:
            return ""
        return f"""

This is a bounded targeted revision attempt. Preserve content from the previous
draft that is supported by the supplied context. Change or remove only claims
implicated by the verifier feedback. Do not introduce new factual details. Use
only the supplied context, keep the same task intent and citation requirements,
and return a complete JSON ResearchResult. The revised answer will be verified
again; the feedback does not prove it correct.

Previous draft answer: {previous_draft}

Verifier correction feedback: {correction_feedback or "No additional feedback was supplied."}
"""
