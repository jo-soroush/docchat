# DocChat V1

**A local-first, multi-document, evidence-grounded AI research assistant with hybrid retrieval, citations, verification, and bounded correction.**

DocChat helps users research their own PDF, DOCX, TXT, and Markdown documents locally.

V1 started from the IBM Skills Network DocChat baseline and evolved it into a vendor-neutral, Ollama-based research system with stronger document provenance, multi-document reasoning, evidence grounding, structured verification, safe failure handling, and reproducible evaluation.

The goal of V1 was not simply to make a chatbot answer questions about documents. It was to build a research workflow where answers can be traced to active source material, checked before presentation, and rejected safely when sufficient support is unavailable.

---

## Why I Built This

A basic RAG pipeline can retrieve relevant text and send it to a language model. That alone does not guarantee that citations support claims, multiple uploaded documents remain isolated, comparisons use every required source, large documents embed reliably, or retries improve failed answers.

V1 focuses on those reliability boundaries.

---

## What V1 Can Do

- **Ask** — answer questions using hybrid retrieval.
- **Summarize** — create grounded document synthesis.
- **Key Points** — extract important ideas from active documents.
- **Compare Sources** — compare multiple documents using evidence from each source.
- **Explain Concept** — explain a concept using retrieved document evidence.
- **Generate Study Questions** — generate grounded study material.

Supported formats: PDF, DOCX, TXT, and Markdown.

---

## Core Architecture

```text
Gradio UI
  → Product Adapter / typed EvidenceIntent
  → Docling / Markdown-aware chunking / bounded subchunking / cache / provenance
  → BM25 + Chroma vector retrieval
  → task-aware evidence selection
  → typed ResearchResult
  → citation resolution / multi-source grounding
  → typed VerificationResult
  → bounded correction + targeted draft revision
  → VERIFIED or explicit safe failure

DocChat Core
  → ChatProvider + EmbeddingProvider
  → Ollama adapters
```

The application layer remains vendor-neutral; Ollama-specific behavior stays at the provider boundary.

---

## Evidence-Grounded Research

### Questions

**Ask** and **Explain Concept** use ordinary hybrid RAG, combining lexical and semantic retrieval.

### Document Synthesis

**Summarize**, **Key Points**, and **Generate Study Questions** use deterministic, bounded active-document evidence. For large structured documents, V1 uses section-aware coverage with a deterministic fallback when useful section metadata is unavailable.

### Multi-Document Comparison

**Compare Sources** balances evidence across active documents and requires valid claim-to-evidence mappings from every required source. Merely retrieving both documents is not enough to mark a comparison as grounded.

Comparison evidence is bounded by `SYNTHESIS_EVIDENCE_MAX_CHUNKS` (default: 12).
Within that fixed capacity, the selector samples participating sources so one source
cannot silently dominate. It does not promise representative evidence for an
arbitrary number of active documents beyond that bounded capacity.

---

## Hybrid Retrieval

DocChat combines:

- **BM25** for exact words, phrases, names, and lexical matches.
- **Chroma vector retrieval** for semantic similarity.

This hybrid layer supports question-oriented retrieval without relying exclusively on one retrieval method.

---

## Source Provenance and Citations

Each active document and chunk carries stable provenance:

```text
document → document_id → chunk → chunk_id → research claim → resolved citation
```

Citation resolution validates requested chunk IDs against evidence actually supplied to the workflow. Unknown or unavailable IDs do not silently become valid citations.

For comparisons, the workflow additionally checks that every required active source is represented by grounded mappings.

---

## Verification Before Presentation

Research output is not automatically trusted.

A separate Verification Agent returns a strict typed result describing whether the answer is supported, relevant, contradictory, or requires correction.

Supported and unsupported states are structurally separated, preventing contradictory control states from being accepted.

Only `supported=true` and `relevant=true` can route to `VERIFIED`.

---

## Bounded Correction and Retry

Verification failures do not create an unlimited autonomous loop.

```text
Research
  → Verification
  → typed correction feedback
  → targeted revision of the previous draft
  → Verification
```

The retry receives only the immediately relevant correction state. The Research
Agent is instructed to preserve supported content, revise or remove problematic
claims, avoid new factual details, and stay inside the supplied evidence. Its
revised output is independently validated through citation grounding and
verification; verification remains authoritative after every revision.

---

## Engineering Challenges Solved in V1

### Oversized document chunks

Real PDFs produced very large Markdown sections that exceeded practical embedding limits.

**Solution:** deterministic embedding-safe subchunking while preserving section/source provenance.

### Large embedding requests

Embedding thousands of chunks in one request could fail.

**Solution:** provider-owned ordered embedding batching with configurable batch size, stable ordering, partial-batch support, vector-count validation, and safe failure behavior.

### Effective context-window exhaustion

Better section-aware evidence coverage increased prompt size.

**Solution:** validated, configurable Ollama context capacity forwarded through the provider boundary.

### Multi-document grounding

Retrieving two documents did not prove the generated comparison actually used both.

**Solution:** require valid resolved evidence mappings from every active comparison source.

### Unsupported compound claims

A valid citation can still support only part of a broad model claim.

**Solution:** atomic comparison-claim instructions, strict evidence mapping, and independent verification.

### Unguided retries

Full regeneration after verification failure could introduce new unsupported claims.

**Solution:** pass typed verifier correction feedback only to the next bounded research attempt.

### Expensive full regeneration

Recreating an entire answer could discard already-supported content.

**Solution:** targeted revision of the immediately previous draft.

### Structured verification truncation

Real comparison verification exposed a generation-capacity boundary.

**Solution:** measure the failure at the provider boundary, calibrate the verifier, and increase its bounded output budget from 300 to **400 tokens**. Partial/truncated verification results remain rejected.

---

## Safe Failure Is a Feature

DocChat never represents unverified output as `VERIFIED`. A
`RETRY_EXHAUSTED` outcome may preserve and display the latest draft together with
an explicit non-success verification report, rather than presenting that draft
as trusted.

Controlled failures include insufficient comparison sources, invalid evidence mappings, malformed structured output, provider failure, output truncation, unsupported claims, and exhausted bounded retries.

---

## V1 Validation

### Deterministic suite

**145 / 145 tests passed**

Coverage includes product operations, evidence semantics, active-document scoping, retrieval, citations, comparison grounding, embedding-safe chunking, provider boundaries, verification semantics, correction-guided retries, targeted draft revision, routing, traces, and safe failure behavior.

### Retrieval evaluation

**C06: PASS**

### Answer and verification evaluation

**C07: 10 / 10 PASS**

### Real local validation

V1 was exercised through the Gradio application with real uploaded documents.

Validated operations:

- Ask
- Summarize
- Key Points
- Explain Concept
- Generate Study Questions
- Compare Sources

Repeated two-document comparison validation produced citations from both documents, `Supported: YES`, `Relevant: YES`, no unsupported claims, no contradictions, and no provider/output truncation failure.

These results demonstrate the tested V1 behavior; they are not a claim of universal model accuracy.

---

## Local-First Provider Architecture

V1 runs without an active IBM, Watsonx, or OpenAI runtime dependency.

```text
Agents / Retrieval
  → ChatProvider + EmbeddingProvider
  → Ollama implementation
```

The repository does not contain model weights.

---

## Quick Start

V1 was verified on macOS with Python 3.11.15.

```bash
git clone <your-fork-or-clone-url>
cd docchat

python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Install/start Ollama separately and inspect available models:

```bash
ollama --version
ollama list
```

Example configuration used for final local V1 validation:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen3.5:9b
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_EMBEDDING_BATCH_SIZE=32
OLLAMA_CONTEXT_WINDOW=8192
DOCUMENT_CHUNK_MAX_CHARACTERS=4000
GRADIO_SERVER_PORT=7860
MAX_VERIFICATION_RETRIES=2
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION_NAME=documents
SYNTHESIS_EVIDENCE_MAX_CHUNKS=12
```

This records the calibrated validation configuration; repository defaults may differ. Use model names available in your local Ollama installation.

Start DocChat:

```bash
python app.py
```

Open the local Gradio URL, normally `http://127.0.0.1:7860`.

---

## Configuration

| Variable | Purpose |
|---|---|
| `OLLAMA_BASE_URL` | Local Ollama service |
| `OLLAMA_CHAT_MODEL` | Chat model used by agents |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model used by vector retrieval |
| `OLLAMA_EMBEDDING_BATCH_SIZE` | Bounded texts per embedding request |
| `OLLAMA_CONTEXT_WINDOW` | Ollama chat context capacity |
| `DOCUMENT_CHUNK_MAX_CHARACTERS` | Embedding-safe document chunk limit |
| `GRADIO_SERVER_PORT` | Local Gradio port |
| `MAX_VERIFICATION_RETRIES` | Maximum bounded re-research attempts |
| `CHROMA_DB_PATH` | Persistent local vector-store path |
| `CHROMA_COLLECTION_NAME` | Chroma collection |
| `SYNTHESIS_EVIDENCE_MAX_CHUNKS` | Bounded synthesis/comparison evidence capacity |

Copy `.env.example` to `.env`. Never commit `.env`.

---

## Reproduce the V1 Checks

```bash
venv/bin/python -m unittest discover -s test -v
venv/bin/python -m evaluation.run_retrieval_evaluation
venv/bin/python -m evaluation.run_answer_verification_evaluation
venv/bin/python -m pip check
venv/bin/python -m compileall -q agents app.py config document_processor evaluation product providers retriever test utils
```

See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/VERIFIED_DEMOS.md`](docs/VERIFIED_DEMOS.md)
- [`docs/PROVENANCE_AND_DECISIONS.md`](docs/PROVENANCE_AND_DECISIONS.md)

---

## Technology Stack

Python 3.11 · LangGraph · LangChain · Ollama · Docling · Chroma · BM25 · Pydantic · Gradio

Qwen is a model family used in the final local validation configuration, not a
required repository dependency or the default configured model.

---

## What I Learned From V1

The central lesson was that reliable document AI is not primarily about connecting a larger model to a vector database.

Reliability depends on the boundaries around the model: what evidence enters context, how documents retain identity, how claims map to evidence, how multiple sources remain represented, how structured output is validated, how generation budgets are measured, how failures are exposed, and how retries are constrained.

Real-document failures occurred even when individual components appeared correct in isolation.

That shifted the engineering question from:

> “Can the model produce an answer?”

to:

> **“Can the system demonstrate why this answer should be trusted?”**

That became the central design principle of DocChat V1.

---

## Current Limitations

V1 is a local, single-user research system, not a production SaaS deployment.

Current boundaries:

- Ollama is the implemented local provider.
- Real-model quality depends on the selected model.
- No authentication or multi-user isolation.
- No cloud-provider failover.
- No production telemetry backend.
- No persistent research-library experience yet.
- Persistent Chroma representation migration/cleanup remains future work.
- Real-document validation covers selected workflows/documents rather than universal model behavior.

---

## V2 Direction

V2 starts from the closed and validated V1 baseline.

Potential future work may include persistent research libraries, richer source routing, additional tools, provider expansion, security/deployment boundaries, improved observability, broader evaluation, and production-oriented infrastructure.

These are roadmap items, not current V1 capabilities.

---

## Project Provenance

DocChat V1 builds on the historical **IBM Skills Network DocChat** project.

Selected historical baseline:

```text
IBM remote: origin/2-final
Commit: eb9be30
```

V1 preserves that provenance while removing the active IBM runtime dependency and extending the project with the architecture, reliability controls, product semantics, evaluation, and local-provider work documented in this repository.

See [`docs/PROVENANCE_AND_DECISIONS.md`](docs/PROVENANCE_AND_DECISIONS.md) for the detailed distinction between the historical baseline and subsequent V1 engineering work.

No `LICENSE*` file was present in the audited baseline or active repository. Do not infer redistribution or relicensing rights from this README.

---

## Status

**DocChat V1: CLOSED ✅**

V1 reached its defined quality gate after deterministic regression testing, evaluation runners, and real local document validation.

The next development phase is intentionally separated as V2.
