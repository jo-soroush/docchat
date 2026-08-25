# V1 Architecture

## Design principle

V1 separates deterministic product and RAG responsibilities from model-provider
implementation details:

```text
DocChat Core → Provider Abstraction → Local / Cloud Providers
```

Ollama is the only active provider implementation. Cloud/API providers are future
adapters and are not imported by the core.

## Runtime flow and ownership

```text
Gradio UI (`app.py`)
  ├─ `product/operations.py`: validate study operation and construct typed request
  ├─ `DocumentProcessor`: file validation, SHA-256 cache key, Docling conversion,
  │   Markdown header chunking, provenance attachment, deduplication
  └─ `RetrieverBuilder`: Chroma vector retrieval + BM25 + weighted ensemble
       → bounded active-document evidence collector for synthesis/comparison
       ↓
  `AgentWorkflow` (LangGraph)
    retrieval → relevance → research → verification → route / terminal
       ↓                 ↑                 │
  C05 citations          └── bounded re-research (C03 retry budget)
       ↓
  answer, verification report, citation report, C08 safe run trace
```

### Product and UI

`app.py` owns Gradio controls, example loading, and session-level retriever reuse.
It does not retrieve, generate, verify, route, or format citations itself.
`product/operations.py` validates each operation, creates an `OperationRequest`,
and calls `AgentWorkflow.full_pipeline()` once. Its typed `EvidenceIntent` is
`QUESTION` for Ask/Explain Concept, `DOCUMENT_SYNTHESIS` for Summarize/Key
Points/Generate Study Questions, and `MULTI_DOCUMENT_COMPARISON` for Compare
Sources. The product adapter does not implement retrieval, citation resolution,
verification, retries, or tracing.

### Documents and retrieval

`DocumentProcessor` accepts PDF, DOCX, TXT, and Markdown uploads. It hashes
content, uses a short-lived local pickle cache, converts with Docling, splits
Markdown headers, deduplicates chunk content, and attaches stable
`document_id`/`chunk_id` metadata. It reports controlled zero-document, parser,
cache, and partial-upload failures.

`RetrieverBuilder` creates a Chroma vector store from the injected
`EmbeddingProvider`, a BM25 retriever, and a LangChain weighted `EnsembleRetriever`
(`0.4` BM25, `0.6` vector by default). C05 `chunk_id` is the Chroma record ID,
so re-ingesting the same chunk upserts rather than duplicates it. The configured
collection is explicit, and vector searches are filtered to the active upload's
`document_id` values; BM25 is built from that same active document set. Legacy
default-collection data is left untouched and is not queried by the scoped
collection. C06 evaluates all three modes at the same K without claiming the
small fixture proves hybrid superiority.

For `QUESTION`, the evidence wrapper delegates to this unchanged hybrid query
path. For `DOCUMENT_SYNTHESIS`, it selects at most
`SYNTHESIS_EVIDENCE_MAX_CHUNKS` using deterministic section-aware coverage:
it chooses ordered section representatives, preserves early structural coverage,
and spreads any remaining capacity across later sections. When fewer than two
meaningful section labels exist, it uses a deterministic evenly spaced fallback.
For `MULTI_DOCUMENT_COMPARISON`, it requires at least two active `document_id`
values and samples each participating source under the same bounded budget, so
one source cannot silently dominate. These paths preserve the same C05 chunk
metadata used by deterministic citation resolution; they do not query inactive
persisted documents or feed an unrestricted corpus to the model.

### Provider boundary

Core agents and retrieval use only `ChatProvider` and `EmbeddingProvider` from
`providers/contracts.py`. `providers/ollama.py` contains the only active
Ollama-specific client implementation; `providers/factory.py` composes it from
`Settings`. Provider failure is expressed as `ProviderError`.

For typed agent calls, `ChatProvider.generate_structured()` receives the
agent-owned JSON schema rather than an Ollama type. The Ollama adapter applies
its native schema `format` and disables its separate thinking channel, then the
agent's existing strict Pydantic contract validates the returned JSON. A
length-stopped structured completion becomes a safe provider failure before any
partial JSON reaches Pydantic. The core does not parse model prose or
provider-specific reasoning content.

### Workflow contracts and termination

`agents/contracts.py` defines strict Pydantic contracts:

- `RelevanceResult` controls relevance routing.
- `ResearchResult` carries a draft answer and proposed claim-to-chunk mappings.
- `VerificationResult` controls retry/terminal routing through booleans, not
  human-readable report text.
- `TerminalOutcome` is `VERIFIED`, `OUT_OF_SCOPE`, `RETRY_EXHAUSTED`, or
  `FAILURE`.

The workflow permits at most `MAX_VERIFICATION_RETRIES` correction attempts.
Infrastructure or malformed-output failures terminate as `FAILURE`; they do not
become verified answers or consume verification retry budget.

### Citations and trace safety

The research model can propose `ClaimSource` chunk IDs, but
`agents/citations.py` resolves them only against current retrieved chunks.
Unknown IDs become an explicit unavailable citation; DocChat does not fabricate
attribution.

`RunTrace` records a run ID, retrieved chunk IDs, typed decisions, route/retry
events, stage latency, total duration, terminal outcome, and safe error text. It
intentionally excludes raw questions, documents, prompts, answers, model output,
credentials, and raw exception details.

## Quality boundaries

| Layer | What V1 measures | What it does not prove |
| --- | --- | --- |
| C06 retrieval | Hit Rate@K and Recall@K on a fixed corpus | Broad real-embedding quality |
| C07 answer/workflow | Deterministic answer, citation, verification, routing cases | Universal real-model behavior |
| C08 trace | Safe diagnosability of workflow paths | Telemetry backend or persistent tracing |
| C09 failures | Controlled known failure paths | Cloud resiliency or provider failover |
| C10 product | Operation routing through the same backend | Production UX/usability research |

## Extension boundary

V2 may add source routing, registered tools, multi-step research, security,
persistent collections, monitoring, and deployment only through approved Cards.
None of those capabilities are implied by this architecture document.
