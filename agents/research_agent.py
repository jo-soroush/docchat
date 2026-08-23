"""Research answer generation behind a typed model-output contract."""

from langchain.schema import Document

from providers.contracts import ChatProvider

from .citations import build_citation_context, resolve_claim_sources
from .contracts import ResearchResult


class ResearchAgent:
    def __init__(self, model: ChatProvider):
        self.model = model

    def generate_prompt(self, question: str, context: str) -> str:
        return f"""
You are an AI assistant designed to provide precise factual answers from the given context.

Answer the question using only the context. Return ONLY a JSON object with this exact schema:
{{"draft_answer":"clear concise answer","claim_sources":[{{"claim":"important factual claim","chunk_ids":["chunk ID from context"]}}]}}

For every important factual claim, include only chunk IDs shown in the context. If no source can be mapped, return an empty claim_sources array. Do not invent IDs.

Question: {question}
Context: {context}
"""

    def generate(self, question: str, documents: list[Document]) -> ResearchResult:
        context = build_citation_context(documents)
        response_text = self.model.generate_structured(
            self.generate_prompt(question, context),
            schema=ResearchResult.model_json_schema(),
            temperature=0.3,
            max_tokens=300,
        )
        result = ResearchResult.from_model_json(response_text)
        return result.model_copy(
            update={"citations": resolve_claim_sources(result.claim_sources, documents)}
        )
