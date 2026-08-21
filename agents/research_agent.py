"""Research answer generation behind a typed model-output contract."""

from langchain.schema import Document

from providers.contracts import ChatProvider

from .contracts import ResearchResult


class ResearchAgent:
    def __init__(self, model: ChatProvider):
        self.model = model

    def generate_prompt(self, question: str, context: str) -> str:
        return f"""
You are an AI assistant designed to provide precise factual answers from the given context.

Answer the question using only the context. Return ONLY a JSON object with this exact schema:
{{"draft_answer":"clear concise answer"}}

Question: {question}
Context: {context}
"""

    def generate(self, question: str, documents: list[Document]) -> ResearchResult:
        context = "\n\n".join(doc.page_content for doc in documents)
        response_text = self.model.generate(
            self.generate_prompt(question, context),
            temperature=0.3,
            max_tokens=300,
        )
        return ResearchResult.from_model_json(response_text)
