"""Relevance classification behind a typed model-output contract."""

import logging

from providers.contracts import ChatProvider

from .contracts import RelevanceDecision, RelevanceResult

logger = logging.getLogger(__name__)


class RelevanceChecker:
    def __init__(self, model: ChatProvider):
        self.model = model

    def check(self, question: str, retriever, k: int = 3) -> RelevanceResult:
        """Classify retrieved evidence without exposing raw model text to routing."""
        logger.debug("RelevanceChecker.check called with k=%s", k)
        top_docs = retriever.invoke(question)
        if not top_docs:
            return RelevanceResult(
                decision=RelevanceDecision.NO_MATCH,
                explanation="The retriever returned no document chunks.",
            )

        document_content = "\n\n".join(doc.page_content for doc in top_docs[:k])
        prompt = f"""
You are an AI relevance checker between a user question and document content.

Classify whether the passages can answer the question. Return ONLY a JSON object with this exact schema:
{{"decision":"CAN_ANSWER|PARTIAL|NO_MATCH","explanation":"brief reason"}}

CAN_ANSWER means the passages fully answer the question. PARTIAL means they discuss the topic but are incomplete. NO_MATCH means they do not discuss the topic.

Question: {question}
Passages: {document_content}
"""
        response_text = self.model.generate_structured(
            prompt,
            schema=RelevanceResult.model_json_schema(),
            temperature=0,
            max_tokens=100,
        )
        result = RelevanceResult.from_model_json(response_text)
        logger.debug("Structured relevance decision: %s", result.decision.value)
        return result
