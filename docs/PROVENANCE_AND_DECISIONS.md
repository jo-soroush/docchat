# Provenance and V1 Design Decisions

## Historical baseline

DocChat began from IBM Skills Network repository history retained in this Git
repository. The audited historical reference is:

- IBM remote: `https://github.com/ibm-developer-skills-network/nlhhh-docchat.git`
- Selected baseline branch/commit: `origin/2-final` at `eb9be30` (`update embeddings`)

The historical baseline directly constructed Watsonx models and embeddings and
depended on IBM credentials, project access, endpoint configuration, and runtime
services. V1 preserves that history as provenance but does not retain it as an
active runtime dependency.

No `LICENSE*` or `README*` provenance file existed in the audited historical
baseline. This repository therefore records the absence rather than asserting an
upstream license. Review upstream terms and obtain appropriate permission before
redistribution, relicensing, or commercial use.

## Baseline preserved versus V1 extension

| Preserved useful behavior | V1 extension / correction |
| --- | --- |
| PDF/DOCX/TXT/MD uploads; Docling conversion; Markdown chunks; cache/deduplication | Vendor-neutral chat/embedding contracts and Ollama adapters |
| Chroma vector search, BM25, hybrid retrieval | Cross-platform direct dependency manifest and local configuration |
| Relevance, research, verification, LangGraph workflow concept | Bounded retry/terminal outcomes and strict Pydantic control contracts |
| Gradio UI and session retriever reuse | Stable chunk provenance, citations, evaluation suites, safe traces, controlled failures, and study operations |

V1 deliberately did **not** preserve IBM credentials, project IDs, endpoint
requirements, Watsonx SDK imports, or hosted IBM runtime services.

## Key V1 decisions

1. **Provider independence (C02):** Core consumes `ChatProvider` and
   `EmbeddingProvider`; Ollama is local-first. Future providers must remain
   adapters behind this boundary.
2. **Bounded workflow (C03):** verification correction has a configured finite
   budget and explicit terminal outcomes.
3. **Structured control state (C04):** routing uses validated Pydantic values,
   not formatted model report text.
4. **Grounded attribution (C05):** claims map to current retrieved chunk IDs;
   missing mappings are visible rather than invented.
5. **Measured quality layers (C06/C07):** retrieval is evaluated separately from
   answer, citation, verification, and routing behavior.
6. **Safe observability and failures (C08/C09):** content-free traces make paths
   diagnosable, and known failures remain explicit rather than fluent.
7. **Thin product adapter (C10):** study operations reuse the proven backend
   instead of creating UI-side RAG logic.

## Active repository and remotes

`github` is the personal/project remote containing the active
`docchat-v1-baseline` V1 branch. `origin` remains the IBM provenance remote.
V1 governance prohibits writes to `origin`.

## Known V1 limitations

- Real Ollama queries require locally available chat and embedding models that
  comply with the structured JSON outputs expected by the workflow.
- The deterministic fixtures are intentionally small and are not a claim of
  universal retrieval or model-answer quality.
- V1 has no cloud provider, authentication, multi-user isolation, persistent
  research library, telemetry backend, provider failover, or production
  deployment boundary.
- The historical `test/test1.py` Docling diagnostic includes a deliberately
  malformed PNG-as-PDF path and may require locally cached Docling assets; it is
  not the deterministic acceptance suite.

See `01_DOCCHAT_ROADMAP.md` for approved V2 work. V2 is not active in V1.
