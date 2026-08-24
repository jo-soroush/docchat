"""Verification behind a typed model-output contract."""

from langchain.schema import Document

from providers.contracts import ChatProvider
from retriever.evidence import EvidenceIntent

from .contracts import VerificationResult


class VerificationAgent:
    def __init__(self, model: ChatProvider):
        self.model = model

    def generate_prompt(
        self, question: str, answer: str, context: str, intent: EvidenceIntent
    ) -> str:
        return f"""
You verify an answer against the exact user question and the supplied evidence.

Apply these control-field definitions exactly:
- supported: every factual claim made by the answer is supported by the supplied evidence.
- relevant: the answer directly responds to the exact user question.
- contradictions: list only conflicts between the answer and the supplied evidence.
- unsupported_claims: list only claims made by the answer that lack support in the supplied evidence.

Apply these control-state consistency rules before returning JSON:
- If supported is true, unsupported_claims MUST be [] and contradictions MUST be [].
- If unsupported_claims is non-empty, supported MUST be false.
- If contradictions is non-empty, supported MUST be false.
- If supported is false, provide an exact evidence-grounded reason through
  unsupported_claims, contradictions, or correction_feedback as appropriate.
- Do not return a supported=true result that also lists any unsupported claim or contradiction.

Do not use external or model knowledge. Do not require coverage of related concepts
that the user did not ask for. Do not penalize a scoped answer merely because the
broader retrieved evidence contains additional information. An omitted detail is not
a contradiction unless the exact user question requires that detail for a complete answer.

Verification task intent: {intent.value}
{self._intent_semantics(intent)}

Return ONLY one of these mutually exclusive JSON shapes:
- Supported: {{"supported":true,"relevant":true,"unsupported_claims":[],"contradictions":[],"correction_feedback":""}}
- Unsupported: {{"supported":false,"relevant":true,"unsupported_claims":["claim lacking evidence"],"contradictions":[],"correction_feedback":"how to improve the answer"}}

Use JSON booleans, not YES/NO strings. Use empty arrays and an empty string when there is nothing to report.

Question: {question}
Answer: {answer}
Evidence: {context}
"""

    def check(
        self,
        question: str,
        answer: str,
        documents: list[Document],
        intent: EvidenceIntent = EvidenceIntent.QUESTION,
    ) -> VerificationResult:
        context = "\n\n".join(doc.page_content for doc in documents)
        response_text = self.model.generate_structured(
            self.generate_prompt(question, answer, context, intent),
            schema=VerificationResult.model_json_schema(),
            temperature=0.0,
            max_tokens=400,
        )
        return VerificationResult.from_model_json(response_text)

    @staticmethod
    def _intent_semantics(intent: EvidenceIntent) -> str:
        """Describe the typed product task without changing control contracts."""
        if intent is EvidenceIntent.DOCUMENT_SYNTHESIS:
            return """
For DOCUMENT_SYNTHESIS, judge whether the answer is a grounded, responsive synthesis
of the supplied evidence for the requested synthesis operation or focus. Do not require
exhaustive coverage of every evidence chunk or every document topic. Do not treat the
synthesis instruction as a factual question. Reject claims that rely on external
knowledge or lack support in the supplied synthesis evidence.
"""
        if intent is EvidenceIntent.MULTI_DOCUMENT_COMPARISON:
            return """
For MULTI_DOCUMENT_COMPARISON, judge whether comparative claims are grounded in the
supplied evidence and actually address the requested comparison. Do not allow one source
to silently stand in for another when the answer makes a comparison. Do not introduce
external knowledge. Source attribution remains resolved deterministically outside this
verification report.
"""
        return """
For QUESTION, judge whether the answer directly responds to the exact user question and
whether every factual claim is supported by the supplied evidence.
"""
