"""Verification behind a typed model-output contract."""

from langchain.schema import Document

from providers.contracts import ChatProvider

from .contracts import VerificationResult


class VerificationAgent:
    def __init__(self, model: ChatProvider):
        self.model = model

    def generate_prompt(self, question: str, answer: str, context: str) -> str:
        return f"""
You verify an answer against the exact user question and the supplied evidence.

Apply these control-field definitions exactly:
- supported: every factual claim made by the answer is supported by the supplied evidence.
- relevant: the answer directly responds to the exact user question.
- contradictions: list only conflicts between the answer and the supplied evidence.
- unsupported_claims: list only claims made by the answer that lack support in the supplied evidence.

Do not use external or model knowledge. Do not require coverage of related concepts
that the user did not ask for. Do not penalize a scoped answer merely because the
broader retrieved evidence contains additional information. An omitted detail is not
a contradiction unless the exact user question requires that detail for a complete answer.

Return ONLY a JSON object with this exact schema:
{{
  "supported": true,
  "relevant": true,
  "unsupported_claims": ["claim"],
  "contradictions": ["contradiction"],
  "correction_feedback": "how to improve the answer when needed"
}}

Use JSON booleans, not YES/NO strings. Use empty arrays and an empty string when there is nothing to report.

Question: {question}
Answer: {answer}
Evidence: {context}
"""

    def check(
        self, question: str, answer: str, documents: list[Document]
    ) -> VerificationResult:
        context = "\n\n".join(doc.page_content for doc in documents)
        response_text = self.model.generate_structured(
            self.generate_prompt(question, answer, context),
            schema=VerificationResult.model_json_schema(),
            temperature=0.0,
            max_tokens=300,
        )
        return VerificationResult.from_model_json(response_text)
