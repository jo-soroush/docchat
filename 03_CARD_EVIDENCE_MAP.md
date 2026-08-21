# DocChat Card Evidence Map

## Purpose

This file records verified proof of DocChat implementation and Card progress.

Rules:
- repository evidence only;
- never infer completion from chat;
- never claim a test passed unless it actually ran;
- use `Pending`, `Blocked`, or `Not applicable` when proof is unavailable;
- update incrementally after validated implementation steps;
- preserve IBM baseline/provenance evidence.

## Project Checkpoint

| Item | Evidence |
|---|---|
| Project | DocChat |
| Selected baseline | IBM Skills Network final lab implementation |
| Local repository | `~/john/my_projhects/docchat-final` |
| Baseline branch | `docchat-v1-baseline` |
| Tracking baseline | `origin/2-final` |
| Known baseline commit from migration checkpoint | `eb9be30 — update embeddings` |
| Custom extensions at migration checkpoint | Not started |
| First required work | V1-C01 inspect-only architecture/contract/risk audit |
| Current evidence status | Must be re-verified from repository before implementation |

> The checkpoint above comes from the migration handoff and is not a substitute for current Git/repository verification.

## Project-Owner Architecture Decision — 2026-08-21

The IBM Skills Network implementation remains in Git history and evidence as the historical baseline. The active DocChat product is now independent and vendor-neutral: it must not depend on IBM Watsonx credentials, projects, SDKs, or runtime services.

Target architecture:

```text
DocChat Core → Provider Abstraction → Local / Cloud Providers
```

- **Core:** document ingestion, cache/deduplication, persistent document/library direction, BM25/vector/hybrid retrieval, workflow state/routing, verification contracts, and UI adapters.
- **First provider:** Ollama for local chat and embeddings.
- **Future providers:** OpenAI-compatible APIs, AWS/cloud-hosted services, and others behind the same provider contracts.
- **Migration authority:** V1-C02. V1-C01 records the boundary and does not perform the migration.

---

# V1 Evidence

## V1-C01 — Baseline Preservation & Architecture Audit

**Status:** READY FOR HUMAN REVIEW — revised Exit Gate and Card Quality Gate are evidenced; await owner approval to close/merge.

### Implementation / Inspection
- Repository/file ownership map: `app.py` owns the Gradio adapter/session state; `document_processor/file_handler.py` owns validation, Docling conversion, Markdown splitting, cache, and deduplication; `retriever/builder.py` owns Chroma/BM25/hybrid retrieval; `agents/` owns relevance, research, verification, and LangGraph orchestration.
- End-to-end contract map: Gradio upload/question → `DocumentProcessor.process` → `RetrieverBuilder.build_hybrid_retriever` → `AgentWorkflow.full_pipeline` → relevance → research → verification → Gradio answer/report outputs.
- LangGraph state/nodes/edges/routes/loops/termination: `agents/workflow.py:AgentState` carries question, retrieved documents, answer, verification report, relevance, and retriever. `check_relevance` routes `relevant` to `research` or `irrelevant` to `END`; `research` always leads to `verify`; `verify` routes to `research` when its free-text report contains `Supported: NO` or `Relevant: NO`, otherwise `END`. The re-research route has no counter/limit (known V1-C02 risk; not changed here).
- Research Agent contract: `ResearchAgent.generate(question, documents)` concatenates retrieved chunk text and returns `draft_answer` plus the context used; it invokes the configured Watsonx Llama model.
- Verification Agent contract: `VerificationAgent.check(answer, documents)` invokes the configured Watsonx Granite model and formats a report containing support, unsupported claims, contradictions, relevance, and details. Workflow routing depends on report text.
- document processing/chunk/cache map: allowed upload types are `.txt`, `.pdf`, `.docx`, `.md`; total size is validated; each source file is SHA-256-hashed; Docling exports Markdown; `MarkdownHeaderTextSplitter` splits headers; pickle cache entries expire after seven days; duplicate chunk content is removed across files.
- embeddings/ChromaDB map: `RetrieverBuilder` configures Watsonx `ibm/granite-embedding-278m-multilingual` and creates Chroma at `./chroma_db`.
- BM25/vector/hybrid retrieval map: BM25 and Chroma vector retrievers are combined in `EnsembleRetriever` with configured weights `[0.4, 0.6]`.
- UI/application/session reuse map: `app.py` keeps `{file_hashes, retriever}` in `gr.State`; the retriever is rebuilt only when the upload hash set changes.
- portability findings: a temporary V1-C01 configuration correction proved that the original `OPENAI_API_KEY` was unused while Watsonx SDK initialization was the real blocker. Those source/config/test artifacts were removed before closure because they retained IBM runtime implementation and do not belong to the vendor-neutral target. The finding remains as evidence for V1-C02.
- dependency map: the isolated Git-ignored `venv` uses Python 3.11.15 and the baseline direct dependencies pinned in `requirements.txt`: Gradio, Docling, LangChain components, LangGraph, Pydantic Settings, ChromaDB/BM25, and IBM Watsonx AI. `venv/bin/python -m pip check` reported `No broken requirements found`.
- coupling map: `document_processor/`, Chroma/BM25/ensemble composition, `agents/workflow.py`, prompts/verification format, and `app.py` are reusable core/UI candidates. `agents/relevance_checker.py`, `agents/research_agent.py`, `agents/verification_agent.py`, and `retriever/builder.py` are IBM architectural coupling because they instantiate Watsonx models/embeddings directly. IBM package requirements and Watsonx settings are configuration/runtime coupling. The unbounded re-research route and free-text routing are future V1-C03/C04 risks.
- provenance/license record: Git remote `origin` is `https://github.com/ibm-developer-skills-network/nlhhh-docchat.git`; selected implementation commit is `eb9be30` (`origin/2-final`). No repository `LICENSE*` or `README*` provenance file was found during this audit.
- known limitations: no runtime credentials/project access are present; existing `test/test1.py` is a manual Docling parser script, not an assertion-based automated suite. It references the tracked fixture `test/ocr_test.pdf` and `test/sample.png`.

### Tests / Runtime
- Existing tests discovered: `test/test1.py` is the only historical test-like executable. It is a manual parser diagnostic, not an assertion-based suite; it exercises Docling and LangChain parsing against tracked `test/ocr_test.pdf` and `test/sample.png`.
- Existing tests executed: `venv/bin/python test/test1.py` completed. LangChain/PyPDF parsed the OCR PDF fixture (empty extracted content); the PNG passed to `PyPDFLoader` failed as an invalid PDF (`Stream has ended unexpectedly`); both Docling paths failed because the required Hub model snapshot is not available locally and cannot be downloaded in this environment. The script handles these errors and exits successfully.
- Baseline application run: `venv/bin/python app.py` reached the original Pydantic configuration boundary and failed with `ValidationError: OPENAI_API_KEY — Field required`. Static/SDK inspection established that the setting is unused but Watsonx credentials/project access are required for the original model/embedding path.
- Baseline test questions: Established as deferred V1-C02 local smoke checks: uploaded PDF/TXT/DOCX/MD, multi-document retrieval, hybrid result relevance, research answer, verification report, and out-of-scope response.
- Actual results: `venv/bin/python -m pip check` passed (`No broken requirements found`); AST parsing of all repository Python files passed; the manual parser diagnostic completed with the documented external-model and invalid-input limitations.

### Git / Repository
- Current branch verified: `codex/v1-c01-baseline-audit`, created from `docchat-v1-baseline` at `6e0da73`.
- Tracking/upstream verified: selected IBM baseline is `origin/2-final` commit `eb9be30`; local baseline branch previously tracked `github/docchat-v1-baseline`.
- Working tree verified: temporary Watsonx portability source/config/test artifacts were removed. Intended C01 changes are governance, roadmap, Card specification, evidence, and Git workflow documents only; `venv/` is ignored.
- Baseline commit verified: `eb9be30 — update embeddings`.

### Exit Gate
**PASS — awaiting human closure approval.**

- **Baseline architecture/blockers evidenced:** source, Git history, runtime startup, SDK, and parser diagnostics identify the original IBM workflow and its unavailable credentials/model artifacts.
- **Provenance preserved:** `origin/2-final` at `eb9be30` and the IBM remote are recorded; no history was rewritten or removed.
- **Reusable vs vendor coupling documented:** Core/UI candidates and direct Watsonx architectural/configuration coupling are mapped above.
- **Independent target is authoritative:** governance records `DocChat Core → Provider Abstraction → Local / Cloud Providers`, with Ollama first.
- **Next Card is bounded:** V1-C02 alone owns provider contracts, Ollama implementation, and removal of active IBM runtime dependency. No V1-C02 code was started.

### Remaining
Obtain owner approval to close/merge V1-C01. After merge, and only with separate approval, start V1-C02 on `codex/v1-c02-provider-ollama`. V1-C02 must replace active IBM runtime coupling with the approved provider boundary and local Ollama implementation, preserve provenance, and prove retained core behavior. Never commit `.env`, token files, API keys, bearer tokens, or local model artifacts.

### Learning Record

What we built:
- An evidence-backed baseline/coupling audit, historical-provenance record, and approved independent architecture/Card sequence. Temporary Watsonx portability code was deliberately removed because it was not the target implementation.

Why we built it:
- The inherited IBM lab cannot execute independently, and a safe migration requires knowing what is useful core behavior before replacing vendor-specific infrastructure.

What we inherited / how it works:
1. Gradio accepts documents and a question, and reuses a session retriever when upload hashes are unchanged.
2. DocumentProcessor validates, hashes, caches, deduplicates, converts with Docling, and Markdown-splits content.
3. RetrieverBuilder combines Chroma vector search and BM25 through an ensemble retriever.
4. The LangGraph workflow checks relevance, generates a research answer, verifies it, and may loop back to research from free-text verification output.

Vendor-neutral / reusable:
- Upload handling, Docling/Markdown processing, cache/deduplication, Chroma/BM25 hybrid composition, workflow structure, prompts, verification-report concept, and Gradio session reuse.

IBM-specific / to migrate:
- Direct `ibm_watsonx_ai`/`langchain_ibm` imports, Watsonx model and embedding construction, hard-coded Skills Network project/endpoint, IBM credentials, and IBM-hosted runtime services.

Architecture before → after:
- Before: the active application directly coupled agents and embeddings to IBM Watsonx.
- Target direction: `DocChat Core → Provider Abstraction → Local / Cloud Providers`, with Ollama as first local provider; cloud/API providers follow the same contracts later.

Tests / actual results:
- `venv/bin/python test/test1.py`: completed; LangChain PDF path completed, Docling model snapshot unavailable, and PNG-as-PDF path failed as an expected malformed-input limitation.
- `venv/bin/python -m pip check`: PASS.
- AST parse of all repository Python: PASS.
- Original app startup: BLOCKED by unused `OPENAI_API_KEY` validation before Watsonx authentication; this is documented as historical baseline behavior, not a closure failure under the revised contract.

Problems discovered / diagnosis:
- The baseline depended on unavailable IBM credentials/project/model services, while `OPENAI_API_KEY` was required by settings but unused by runtime code.
- The parser diagnostic depends on an external Docling model snapshot and misuses a PNG as a PDF for its LangChain branch.
- Direct SDK imports inside agents/retriever are architectural coupling, not merely environment configuration.

Professional engineering lesson:
- Preserve provenance and user-facing behavior separately from infrastructure. Audit and classify coupling first; then migrate it through one bounded Card with tests instead of scattering provider conditionals through core logic.

Student takeaway:
- An agentic RAG app is more than its LLM: ingestion, retrieval, workflow, verification, and UI can survive a provider migration when their ownership is explicit. Credentials, SDK imports, and project IDs reveal where a provider boundary is needed.

What V1-C02 changes and why:
- It will introduce the provider contracts, Ollama chat/embedding adapters, local configuration, deterministic fakes, and migration tests needed to remove active IBM runtime dependencies while preserving the documented core behavior.

### CARD_QUALITY_GATE

Status: PASS — awaiting owner approval to close/merge

Focused tests:
- `venv/bin/python test/test1.py` completed with the actual results above.
- AST parse: PASS.

Relevant existing tests:
- The repository contains no assertion-based historical test suite; the sole tracked diagnostic was executed.

Regression checks for prior Cards:
- Not applicable; no prior Card is closed.

Card-specific evaluation / acceptance:
- Baseline/provenance/coupling maps, vendor-neutral target, and bounded V1-C02 contract reviewed against source, Git history, and project-owner decision: PASS.

Exit Gate fully mapped to evidence: YES.
Evidence Map updated: YES.
git diff reviewed: YES — only intended C01 governance, roadmap, specification, evidence, and Git-workflow documents changed.
git status reviewed: YES — no application source, tests, secrets, generated artifacts, or local environment files remain in the C01 checkpoint.
Unrelated changes found: NO; temporary Watsonx portability artifacts were removed.
Secrets / generated artifact check: PASS; no secret/config/model/cache artifact is tracked for C01.
Known limitations: IBM runtime cannot be exercised without external IBM access; Docling diagnostic requires an unavailable external model snapshot; its PNG LangChain branch is malformed by design.
Recommended Card status: READY FOR HUMAN REVIEW.
Human approval required before next Card: YES.

---

## V1-C02 — Provider Boundary & Ollama Local Runtime
**Status:** BLOCKED — requires V1-C01 closure and owner approval; no implementation started.
**Evidence:** Pending.

## V1-C03 — Bounded Research / Verification Loop
**Status:** BLOCKED — dependency chain not satisfied.
**Evidence:** Pending.

## V1-C04 — Structured Agent Contracts
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C05 — Source & Citation Grounding
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C06 — Retrieval Quality Evaluation
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C07 — Answer & Verification Evaluation Suite
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C08 — Observability & Run Trace
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C09 — Robust Error Handling & Fallbacks
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C10 — Research Assistant Product Experience
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C11 — V1 Closure & Portfolio Evidence
**Status:** BLOCKED.
**Evidence:** Pending.

---

# V2 Evidence

All V2 Cards are **BLOCKED / NOT STARTED** until V1 foundations and their required dependencies are closed with verified evidence.

- V2-C01 Agentic Source Router — Pending
- V2-C02 Research Tool Registry — Pending
- V2-C03 ReAct Research Agent — Pending
- V2-C04 Reflexion with External Evidence — Pending
- V2-C05 Specialized Multi-Agent Boundaries — Pending
- V2-C06 Coordinator / Supervisor Routing — Pending
- V2-C07 Advanced Grounded Verification — Pending
- V2-C08 Human-in-the-Loop Review — Pending
- V2-C09 Permissions, Privacy & Security Guardrails — Pending
- V2-C10 Persistent Research Collections & Memory Boundary — Pending
- V2-C11 Production Evaluation & Monitoring — Pending
- V2-C12 Deployment & Multi-User Boundary — Pending

---

## Evidence Entry Template

Use this after each validated bounded step:

```text
Card:
Status:

Implementation:
- File / symbol:
- Verified behavior:

Tests / Evaluation:
- File / case:
- Command/run:
- Actual result:

Architecture / Decision:
- Location:
- Verified decision:

Prompt / Schema / Configuration:
- Location:
- Verified behavior:

Runtime / Trace:
- Evidence:

Git:
- Commit:
- Diff/state:

IBM Baseline Preservation:
- Preserved capability:
- Verification:

Exit Gate:
- Requirement advanced:
- Proof:

Remaining:
- Work still required:
```


---

# Mandatory Learning + Quality Evidence for Every Card

Every Card evidence section must contain both **proof** and **teaching value**.

## Card Learning Record Template

```text
### Learning Record

What we built:
- Plain-language summary of the capability.

Why we built it:
- The engineering problem and why it matters.

Agentic AI / RAG concept:
- The specific concept demonstrated by this Card.
- Clarify whether relevant parts are agents, tools, nodes, deterministic components, retrieval components, or workflow state.

How it works:
1.
2.
3.

Architecture before:
- What the system looked like before the Card.

Architecture after:
- What changed and which ownership boundary now exists.

Important files and ownership:
- File / symbol:
- Responsibility:

Tests / evaluations:
- Exact command or evaluation:
- Actual result:
- Regression coverage:

Problem(s) discovered:
- What failed, surprised us, or disproved an assumption.

Diagnosis / solution:
- How the issue was understood and resolved.

Professional engineering lesson:
- What a production/company engineering team should learn from this.

Student takeaway:
- Short, clear explanation for an Agentic AI learner.

Exit Gate proof:
- Requirement:
- Evidence:

What this enables next:
- Which next Card/boundary is now possible and why.
```

## Card Quality Gate Evidence

```text
### CARD_QUALITY_GATE

Status: PASS | BLOCKED

Focused tests:
Relevant existing tests:
Regression checks for prior Cards:
Card-specific evaluation / acceptance:
Exit Gate fully mapped to evidence:
Evidence Map updated:
git diff reviewed:
git status reviewed:
Unrelated changes found:
Secrets / generated artifact check:
Known limitations:
Recommended Card status:
Human approval required before next Card: YES
```

Rules:
- `PASS` only when every required item succeeds.
- Any failure keeps the Card `IN PROGRESS` or `BLOCKED`.
- Codex must never continue automatically to the next Card.

## Git / GitHub Evidence

For meaningful validated checkpoints record:

```text
### Git / GitHub

Branch:
Commit:
Commit message:
Push status:
Draft PR:
PR status:
Quality Gate before merge:
Human approval:
Merge method:
Merged commit:
Post-merge verification:
```

GitHub is used for traceability and review; it does not replace repository evidence or Card Exit Gate proof.
