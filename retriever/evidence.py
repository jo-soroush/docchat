"""Bounded evidence selection for product intents over active uploaded documents."""

from dataclasses import dataclass
from enum import Enum
from math import ceil
from typing import Any

from langchain.schema import Document


class EvidenceIntent(str, Enum):
    """The evidence semantics required by a product operation."""

    QUESTION = "QUESTION"
    DOCUMENT_SYNTHESIS = "DOCUMENT_SYNTHESIS"
    MULTI_DOCUMENT_COMPARISON = "MULTI_DOCUMENT_COMPARISON"


class EvidenceCollectionError(RuntimeError):
    """Safe product-level failure while collecting active-document evidence."""


@dataclass(frozen=True)
class EvidenceSelection:
    """Bounded active-document evidence handed to the existing workflow."""

    documents: tuple[Document, ...]
    document_ids: tuple[str, ...]
    intent: EvidenceIntent

    @property
    def is_sufficient(self) -> bool:
        if not self.documents:
            return False
        if self.intent is EvidenceIntent.MULTI_DOCUMENT_COMPARISON:
            return len(self.document_ids) >= 2
        return True


class ActiveDocumentEvidenceRetriever:
    """Keep normal hybrid retrieval while adding bounded active-document coverage."""

    def __init__(self, hybrid_retriever: Any, documents: list[Document], max_chunks: int):
        self._hybrid_retriever = hybrid_retriever
        self._documents = tuple(documents)
        self._max_chunks = max_chunks

    def invoke(self, question: str) -> list[Document]:
        """Preserve the established QUESTION hybrid-RAG behavior."""
        return self._hybrid_retriever.invoke(question)

    def collect_evidence(self, intent: EvidenceIntent, question: str) -> EvidenceSelection:
        """Collect only active-upload evidence using the selected typed strategy."""
        if intent is EvidenceIntent.QUESTION:
            documents = tuple(self.invoke(question))
            return EvidenceSelection(
                documents=documents,
                document_ids=self._document_ids(documents),
                intent=intent,
            )

        source_groups = self._active_source_groups()
        if intent is EvidenceIntent.MULTI_DOCUMENT_COMPARISON and len(source_groups) < 2:
            raise EvidenceCollectionError(
                "Compare Sources requires at least two active uploaded documents."
            )

        if intent is EvidenceIntent.DOCUMENT_SYNTHESIS:
            documents = tuple(self._section_aware_balanced_samples(source_groups))
        else:
            documents = tuple(self._balanced_samples(source_groups))
        return EvidenceSelection(
            documents=documents,
            document_ids=tuple(source_groups),
            intent=intent,
        )

    def _active_source_groups(self) -> dict[str, list[Document]]:
        groups: dict[str, list[Document]] = {}
        for document in self._documents:
            metadata = document.metadata or {}
            document_id = metadata.get("document_id")
            chunk_id = metadata.get("chunk_id")
            if not isinstance(document_id, str) or not document_id:
                raise EvidenceCollectionError(
                    "Active document evidence is missing its stable document identity."
                )
            if not isinstance(chunk_id, str) or not chunk_id:
                raise EvidenceCollectionError(
                    "Active document evidence is missing its stable chunk identity."
                )
            if document.page_content.strip():
                groups.setdefault(document_id, []).append(document)
        return groups

    def _balanced_samples(self, source_groups: dict[str, list[Document]]) -> list[Document]:
        """Take deterministic, evenly spaced samples without letting one source dominate."""
        selected_source_ids = list(source_groups)[: self._max_chunks]
        if not selected_source_ids:
            return []
        per_source_limit = max(1, self._max_chunks // len(selected_source_ids))
        selected: list[Document] = []
        for document_id in selected_source_ids:
            selected.extend(self._evenly_spaced(source_groups[document_id], per_source_limit))
        return selected

    def _section_aware_balanced_samples(
        self, source_groups: dict[str, list[Document]]
    ) -> list[Document]:
        """Cover sections per active source while preserving the existing global cap."""
        selected_source_ids = list(source_groups)[: self._max_chunks]
        if not selected_source_ids:
            return []
        per_source_limit = max(1, self._max_chunks // len(selected_source_ids))
        selected: list[Document] = []
        for document_id in selected_source_ids:
            selected.extend(
                self._section_aware_samples(source_groups[document_id], per_source_limit)
            )
        return selected

    def _section_aware_samples(self, documents: list[Document], limit: int) -> list[Document]:
        """Select ordered section representatives with a deterministic sparse-metadata fallback."""
        if len(documents) <= limit:
            return list(documents)

        section_groups: dict[str | None, list[Document]] = {}
        meaningful_sections: set[str] = set()
        for document in documents:
            section = self._section_label(document)
            section_groups.setdefault(section, []).append(document)
            if section is not None:
                meaningful_sections.add(section)

        # A single label (or no labels) cannot improve on positional coverage.
        if len(meaningful_sections) < 2:
            return self._evenly_spaced(documents, limit)

        groups = list(section_groups.values())
        if len(groups) <= limit:
            representatives = [group[0] for group in groups]
            representative_ids = {id(document) for document in representatives}
            remaining = [
                document
                for document in documents
                if id(document) not in representative_ids
            ]
            representatives.extend(
                self._evenly_spaced(remaining, limit - len(representatives))
            )
            return representatives

        # Keep deterministic early structural coverage, then spread the remaining
        # capacity across later sections. This avoids skipping a whole early section
        # merely because a long document has many individually headed chunks.
        early_count = ceil(limit * 2 / 3)
        early_groups = groups[:early_count]
        later_groups = groups[early_count:]
        later_count = limit - len(early_groups)
        return [group[0] for group in early_groups] + [
            later_groups[index][0]
            for index in self._evenly_spaced_indexes(len(later_groups), later_count)
        ]

    @staticmethod
    def _evenly_spaced(documents: list[Document], limit: int) -> list[Document]:
        if limit <= 0:
            return []
        if len(documents) <= limit:
            return list(documents)
        return [
            documents[index]
            for index in ActiveDocumentEvidenceRetriever._evenly_spaced_indexes(
                len(documents), limit
            )
        ]

    @staticmethod
    def _evenly_spaced_indexes(length: int, limit: int) -> list[int]:
        if limit <= 0 or length <= 0:
            return []
        if limit == 1:
            return [0]
        return [index * (length - 1) // (limit - 1) for index in range(limit)]

    @staticmethod
    def _section_label(document: Document) -> str | None:
        metadata = document.metadata or {}
        for key in ("section", "Header 1", "Header 2"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None

    @staticmethod
    def _document_ids(documents: tuple[Document, ...]) -> tuple[str, ...]:
        ids: list[str] = []
        for document in documents:
            document_id = (document.metadata or {}).get("document_id")
            if isinstance(document_id, str) and document_id and document_id not in ids:
                ids.append(document_id)
        return tuple(ids)
