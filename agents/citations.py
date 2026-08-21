"""Deterministic source-citation resolution for retrieved local document chunks."""

from pathlib import Path

from langchain.schema import Document

from .contracts import ClaimSource, SourceCitation


def build_citation_context(documents: list[Document]) -> str:
    """Label evidence with stable chunk identifiers for the research model."""
    rendered_documents: list[str] = []
    for document in documents:
        metadata = document.metadata or {}
        chunk_id = metadata.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            rendered_documents.append(document.page_content)
            continue

        source_label = _source_label(metadata)
        rendered_documents.append(
            f"[chunk_id: {chunk_id}; {source_label}]\n{document.page_content}"
        )
    return "\n\n".join(rendered_documents)


def resolve_claim_sources(
    claim_sources: list[ClaimSource], documents: list[Document]
) -> list[SourceCitation]:
    """Resolve untrusted model IDs only against the current retrieved documents."""
    source_index = {
        document.metadata.get("chunk_id"): document
        for document in documents
        if isinstance(document.metadata.get("chunk_id"), str)
        and document.metadata.get("chunk_id")
    }
    citations: list[SourceCitation] = []

    for claim_source in claim_sources:
        if not claim_source.chunk_ids:
            citations.append(_unavailable_citation(claim_source.claim, None))
            continue

        for chunk_id in claim_source.chunk_ids:
            document = source_index.get(chunk_id)
            if document is None:
                citations.append(_unavailable_citation(claim_source.claim, chunk_id))
                continue
            metadata = document.metadata or {}
            page = metadata.get("page")
            citations.append(
                SourceCitation(
                    claim=claim_source.claim,
                    chunk_id=chunk_id,
                    document_id=_string_metadata(metadata, "document_id"),
                    source_name=_source_name(metadata),
                    section=_section(metadata),
                    page=page if isinstance(page, int) else None,
                    available=True,
                )
            )
    return citations


def format_citation_report(citations: list[SourceCitation]) -> str:
    """Render citations for people; workflow routing never consumes this text."""
    if not citations:
        return "Citations unavailable: the research result did not map claims to retrieved chunks."

    lines = ["Sources and citations:"]
    for citation in citations:
        if not citation.available:
            requested = citation.chunk_id or "no chunk ID"
            lines.append(f"- {citation.claim}: Citation unavailable ({requested}).")
            continue

        details = [citation.source_name or "source metadata unavailable"]
        if citation.section:
            details.append(f"section: {citation.section}")
        if citation.page is not None:
            details.append(f"page: {citation.page}")
        details.append(f"chunk: {citation.chunk_id}")
        lines.append(f"- {citation.claim}: {' | '.join(details)}")
    return "\n".join(lines)


def _unavailable_citation(claim: str, chunk_id: str | None) -> SourceCitation:
    return SourceCitation(
        claim=claim,
        chunk_id=chunk_id,
        document_id=None,
        source_name=None,
        section=None,
        page=None,
        available=False,
        message="The requested chunk is not among the retrieved evidence.",
    )


def _source_label(metadata: dict) -> str:
    details = [_source_name(metadata) or "source metadata unavailable"]
    section = _section(metadata)
    if section:
        details.append(f"section: {section}")
    page = metadata.get("page")
    if isinstance(page, int):
        details.append(f"page: {page}")
    return "; ".join(details)


def _source_name(metadata: dict) -> str | None:
    source_name = _string_metadata(metadata, "source_name")
    if source_name:
        return source_name
    source = _string_metadata(metadata, "source")
    return Path(source).name if source else None


def _section(metadata: dict) -> str | None:
    return (
        _string_metadata(metadata, "section")
        or _string_metadata(metadata, "Header 2")
        or _string_metadata(metadata, "Header 1")
    )


def _string_metadata(metadata: dict, key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) and value else None
