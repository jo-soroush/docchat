"""Verification behind a typed model-output contract."""

from langchain.schema import Document

from providers.contracts import ChatProvider

from .contracts import VerificationResult


class VerificationAgent:
    def __init__(self, model: ChatProvider):
        self.model = model

    def generate_prompt(self, answer: str, context: str) -> str:
        return f"""
You verify whether an answer is supported and relevant to provided context.

Return ONLY a JSON object with this exact schema:
{{
  "supported": true,
  "relevant": true,
  "unsupported_claims": ["claim"],
  "contradictions": ["contradiction"],
  "correction_feedback": "how to improve the answer when needed"
}}

Use JSON booleans, not YES/NO strings. Use empty arrays and an empty string when there is nothing to report.

Answer: {answer}
Context: {context}
"""

    def check(self, answer: str, documents: list[Document]) -> VerificationResult:
        context = "\n\n".join(doc.page_content for doc in documents)
        response_text = self.model.generate(
            self.generate_prompt(answer, context),
            temperature=0.0,
            max_tokens=200,
        )
        return VerificationResult.from_model_json(response_text)
