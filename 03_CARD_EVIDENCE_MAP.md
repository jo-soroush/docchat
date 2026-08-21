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
- V1-C01 checkpoint: `8ff1f44 — docs: close V1-C01 architecture audit` (local only; not pushed, merged, or presented as approval to begin V1-C02).

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
**Status:** READY FOR HUMAN REVIEW — Exit Gate and Card Quality Gate evidenced; no V1-C03 work started.

### Contract Map / Risk Map

- **Before:** `app.py` composed the UI, `RetrieverBuilder` directly constructed Watsonx embeddings, and the relevance, research, and verification agents each directly constructed Watsonx chat models. IBM credentials, project IDs, endpoint, and model IDs were embedded in those runtime owners.
- **Path preserved:** Gradio upload/question → `DocumentProcessor` validation, Docling conversion, Markdown splitting, cache/deduplication → `RetrieverBuilder` Chroma + BM25 weighted ensemble → `AgentWorkflow` relevance → research → verification → Gradio answer/report/session reuse.
- **New boundary:** `providers/contracts.py` owns the minimal `ChatProvider.generate()` and LangChain-compatible `EmbeddingProvider` operations. `providers/ollama.py` alone imports `langchain_ollama`; `providers/factory.py` composes the configured provider bundle. Agents and retriever receive contracts through constructor injection.
- **Risks controlled:** provider failure is wrapped as `OllamaProviderError`; deterministic fakes cover normal unit tests; configuration has no credentials; no cloud adapter, workflow-loop change, schema redesign, or provider marketplace was introduced. The pre-existing unbounded verification re-research route remains explicitly deferred to V1-C03.

### Implementation / Configuration

- `providers/contracts.py`, `providers/ollama.py`, and `providers/factory.py`: vendor-neutral chat/embedding contracts, Ollama adapters, and runtime composition.
- `agents/relevance_checker.py`, `agents/research_agent.py`, `agents/verification_agent.py`, and `agents/workflow.py`: retain prompts, responsibilities, and graph topology while consuming an injected `ChatProvider`; no active IBM SDK import remains.
- `retriever/builder.py`: retains Chroma, BM25, vector retrieval, and `[0.4, 0.6]` ensemble weights while receiving an injected `EmbeddingProvider`.
- `config/settings.py`: removes the unused mandatory `OPENAI_API_KEY`; adds non-secret `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL`, and validated `GRADIO_SERVER_PORT` (default `7860`, range `1..65535`).
- `app.py`: remains the Gradio/session adapter; it composes the generic provider bundle and uses the configured local port. It does not import an Ollama or IBM SDK.
- `.env.example`: documents local non-secret Ollama and Gradio settings; `.env` remains ignored.
- `requirements.txt`: replaced an inherited platform-specific `pip freeze` with direct application dependencies and tested compatibility pins. Watsonx, LangChain IBM, IBM COS, OpenAI, CUDA/NVIDIA, and unrelated transitive pins are absent. `docling-ibm-models` remains a transitive Docling parsing dependency, not an active Watsonx runtime dependency. GPU acceleration is owned by the external Ollama runtime, so no Python CUDA extra is needed for the active application.

### Tests / Runtime

- `venv/bin/python -m pip install --dry-run --ignore-installed --only-binary=:all: -r requirements.txt`: PASS on macOS; resolved the direct manifest without Linux CUDA wheels or an IBM runtime package.
- `venv/bin/python -m pip check`: PASS — `No broken requirements found`.
- `venv/bin/python -m unittest discover -s test -p 'test_provider_boundary.py' -v`: PASS — 10 tests. Covers configuration/default/override/range validation, credential-free provider construction, Ollama adapter success/failure behavior, Chroma + BM25 hybrid retrieval, injected workflow behavior, and active-source vendor-import guard.
- `venv/bin/python test/test1.py`: PASS — exit code `0`. Docling parsed both tracked PDF paths; the known `sample.png` passed to `PyPDFLoader` produced the expected invalid-PDF `Stream has ended unexpectedly` diagnostic.
- `venv/bin/python -m compileall -q app.py agents config document_processor providers retriever`: PASS.
- Active source/requirements scan for Watsonx, LangChain IBM, LangChain OpenAI, IBM project/endpoint/model construction: PASS.
- Provider/retriever/workflow construction: PASS without credentials or an Ollama request.
- Gradio startup: PASS — with `GRADIO_SERVER_PORT=7860`, the app bound `127.0.0.1:7860`, served a successful local HTTP response, and the validation process was shut down. The prior port-5000 collision with macOS ControlCenter is solved through configuration, not process interference.
- Real local Ollama smoke path: PASS using existing Ollama runtime `0.31.2`, chat model `qwen3.5:4b`, and embedding model `qwen3-embedding:0.6b`; no model was downloaded. Real embeddings had dimension `1024`; a temporary Chroma + BM25 hybrid retriever returned one source chunk; real research and verification responses were nonempty.
- Runtime warnings observed but non-blocking: Chroma telemetry-event warnings and torch/Docling accelerator warnings. They did not change results or exit status.

### Known Limitations / Deferrals

- The tiny one-chunk synthetic real smoke case produced relevance `NO_MATCH` despite its source discussing hybrid retrieval. This is an evaluation/prompt-quality observation for V1-C06/V1-C07, not tuned in C02.
- The workflow's existing verification re-research route remains unbounded and is owned exclusively by V1-C03.
- The active defaults in `.env.example` are portable names (`llama3.2` and `nomic-embed-text`); this machine's verified smoke used environment overrides for already-installed Qwen models. A developer must configure/pull suitable local Ollama models before a real query.
- The direct manifest resolves compatible transitive packages through pip. A fully locked, cross-platform deployment artifact is deferred to a later deployment/reproducibility Card; no future AWS/cloud provider was added.

### Learning Record

**What we built / why:** A narrow dependency-inverted boundary lets the RAG core ask for text generation and embeddings without knowing a vendor SDK, credential shape, cloud project, endpoint, or model-client API. It turns an IBM lab runtime into a local-first DocChat runtime while preserving useful ingestion, retrieval, workflow, verification, and UI behavior.

**How it works:**
1. `Settings` reads local non-secret model, endpoint, and port configuration.
2. The provider factory creates Ollama chat and embedding adapters behind small core contracts.
3. The retriever sends texts/queries to the embedding contract; Chroma vector search and BM25 remain combined deterministically.
4. The workflow passes prompts to the chat contract for relevance, research, and verification; the Gradio adapter displays its existing result shape.

**Architecture before → after:**

```text
Before: Gradio/Core → direct Watsonx models + embeddings → IBM credentials/projects/services
After:  Gradio/Core → ChatProvider / EmbeddingProvider → Ollama local runtime
Future: DocChat Core → same contracts → optional Local / Cloud provider adapters
```

**Professional engineering lesson:** Dependency inversion is practical risk control, not abstraction for its own sake. Keep provider-specific HTTP/client details in one adapter, test the core with deterministic fakes, validate one real local integration, and keep operating-system/model concerns outside business and workflow logic. A requirements file should describe the application boundary, not capture every package from one developer's GPU-enabled machine.

**Student takeaway:** An LLM provider produces text; an embedding provider converts text into vectors for similarity search. They are separate dependencies in hybrid RAG. By injecting both behind small interfaces, Chroma/BM25 retrieval and the agent workflow survive a model-provider migration without becoming Ollama- or IBM-specific.

### Exit Gate Proof

- **Local Ollama core path runs:** real configured Ollama embeddings, hybrid retrieval, relevance/research/verification calls, and Gradio startup all passed with no model download.
- **No IBM credential/project/runtime-service dependence:** active source/requirements scan passed; no Watsonx/IBM model construction or credential settings remain.
- **Provider boundary is narrow and testable:** contracts, adapters, factory, deterministic fakes, adapter failure tests, and constructor injection are present.
- **Useful baseline behavior preserved:** Docling diagnostic, Chroma + BM25 hybrid test, workflow construction test, and Gradio session/UI startup all passed.
- **No future Card leakage:** no cloud/AWS/OpenAI adapter, no workflow-loop bound, no structured contract redesign, and no V1-C03 implementation.

### CARD_QUALITY_GATE

**Status: PASS — ready for human review.**

- Focused tests: PASS — 10 V1-C02 provider/configuration/retrieval/workflow tests.
- Relevant existing regression: PASS — `test/test1.py` exit code 0 with documented malformed PNG-as-PDF limitation.
- Card acceptance: PASS — macOS fresh dependency resolution, `pip check`, provider construction, hybrid retrieval, workflow construction, configured Gradio HTTP startup, and real local Ollama smoke path.
- Prior Card regression: PASS — C01 baseline/provenance boundaries remain documented; no history/provenance was removed.
- Exit Gate fully mapped to evidence: YES.
- Evidence Map updated: YES.
- Diff/state/secrets/generated-artifact review: PASS — `git diff --check`, `git status`, changed-file review, ignored `.env` check, and secret-assignment scan completed; no generated runtime artifact remains.
- Known limitations: Chroma telemetry warnings; synthetic relevance `NO_MATCH`; V1-C03 loop bounding deferred; no models are committed.
- Human approval required before V1-C03: YES.

## V1-C03 — Bounded Research / Verification Loop
**Status:** READY FOR HUMAN REVIEW — Exit Gate and Card Quality Gate evidenced; no V1-C04 work started.

### Contract Map / Risk Map

- **Before:** `AgentWorkflow.full_pipeline()` retrieved documents and invoked `AgentState(question, documents, draft_answer, verification_report, is_relevant, retriever)`. The `verify` conditional routed directly back to `research` whenever it considered the free-text report unsuccessful. State had no retry count, no configured limit, and no explicit terminal outcome, so a persistent failed verification could re-enter the cycle indefinitely.
- **Actual routing defect discovered:** `VerificationAgent.format_verification_report()` emits bold labels such as `**Supported:** NO`, while the inherited router searched for `Supported: NO`. The previous re-research condition therefore did not recognize its own formatted failure output. C03 corrects this narrow orchestration predicate without redesigning the agent prompt/parser; typed verification contracts remain V1-C04 work.
- **Preserved path:** Gradio upload/question → document processing/cache/chunking → injected embedding provider → Chroma + BM25 hybrid retriever → relevance → research → verification → Gradio answer/report. Provider contracts and Ollama remain unchanged.
- **Risk controlled:** model/retrieval quality is separate from loop safety. A model can repeatedly request correction, but only the deterministic workflow state and configured policy decide whether another attempt is allowed.

### Implementation / Configuration

- `config/settings.py:Settings.MAX_VERIFICATION_RETRIES`: environment-backed retry budget, default `2`, validated inclusive range `0..5`. It counts re-research attempts after the initial research/verification pass.
- `.env.example`: documents the non-secret local setting.
- `agents/workflow.py:AgentState`: explicitly stores `verification_retries` and `terminal_outcome`.
- `AgentWorkflow`: accepts the existing settings owner, adds deterministic `record_retry`, `mark_verified`, `mark_out_of_scope`, and `mark_retry_exhausted` nodes, and returns retry/outcome metadata alongside the existing answer/report keys. Gradio continues consuming its unchanged answer and report keys.
- Verification success reaches `VERIFIED`; relevance rejection reaches `OUT_OF_SCOPE`; an unsuccessful verification with remaining budget increments state and returns to research; exhausted budget reaches `RETRY_EXHAUSTED` and appends an explicit non-success outcome to the verification report while retaining the last draft answer. Provider/model failures still propagate rather than being falsely reported as verification success; controlled infrastructure fallbacks remain V1-C09 scope.

### Tests / Runtime

- `venv/bin/python -m unittest discover -s test -p 'test_bounded_workflow.py' -v`: PASS — 8 deterministic tests. Proves immediate success, failure then success, repeated failure exhaustion, zero and maximum budgets, out-of-scope termination, configuration range validation, and environment override.
- `venv/bin/python -m unittest discover -s test -p 'test_provider_boundary.py' -v`: PASS — 10 V1-C02 regression tests for provider injection, Ollama adapters, configuration, hybrid retrieval, workflow construction, and active vendor-import guard.
- `venv/bin/python -m unittest discover -s test -v`: PASS — 18 focused/regression tests total.
- `venv/bin/python test/test1.py`: PASS — exit code `0`; retained baseline parser diagnostic executed with its known malformed PNG-as-PDF limitation.
- `venv/bin/python -m pip check`: PASS — `No broken requirements found`.
- `venv/bin/python -m compileall -q app.py agents config document_processor providers retriever test`: PASS.
- Active source/requirements Watsonx, LangChain IBM, LangChain OpenAI, IBM project/endpoint/model construction scan: PASS.
- Application integration: PASS — temporary `GRADIO_SERVER_PORT=7862` process bound `127.0.0.1:7862` and returned HTTP `200`; it was stopped cleanly. Generated `./.gradio/certificate.pem` and `./:memory:.ses` artifacts were inspected and removed.
- Non-blocking warnings observed: the existing LangGraph pending-deprecation warning, Chroma telemetry warnings, and torch/Docling accelerator warnings. They did not alter exit status or test assertions.

### Learning Record

**What we built / why:** A deterministic retry budget around an otherwise probabilistic Research → Verification correction cycle. An agentic system must not let a model-generated failure signal determine how long it continues running.

**How retry state works:** Start with `verification_retries = 0`. Research and verification always receive one initial attempt. On formatted verification failure, the workflow compares the counter with `MAX_VERIFICATION_RETRIES`; if below it, `record_retry` increments state before re-research. Once equal to the limit, the graph takes the explicit exhausted terminal node. With default `2`, a query has at most three research/verification attempts.

**Architecture before → after:**

```text
Before: verify failure → research → verify → ... (no state budget; potentially unbounded)
After:  verify PASS → VERIFIED → END
        verify FAIL + retries remaining → record retry → research
        verify FAIL + budget exhausted → RETRY_EXHAUSTED → END
```

**Important ownership:** Settings owns the configurable policy; `AgentState` owns per-run counter/outcome data; LangGraph routing owns deterministic termination; Research/Verification retain their existing reasoning roles; the UI displays the existing answer/report contract. The provider boundary is not involved in retry policy.

**Professional engineering lesson:** Reliability requires an orchestration budget independent of model quality. Test the route graph with deterministic fakes, count attempts explicitly, and make exhausted work visible to callers instead of silently looping or labeling an unverified answer as verified.

**Student takeaway:** Agentic loops need two different kinds of logic: probabilistic agents can suggest whether more work is useful, but deterministic program state must decide whether more work is permitted. This separates verification quality from a hard termination guarantee.

### Exit Gate Proof

- **No unbounded research/verification loop:** every verification route leads to `VERIFIED`, bounded `record_retry`, or `RETRY_EXHAUSTED`; the counter can increase only until validated configured maximum `5`.
- **Successful verification preserved:** immediate and retry-then-success tests end `VERIFIED` with the expected number of provider calls.
- **Repeated failure is safe and explicit:** exhaustion test terminates after exactly the configured two re-research attempts, preserves the final draft, and reports `RETRY_EXHAUSTED`; the zero-budget test proves the minimum boundary.
- **Baseline and V1-C02 regression preserved:** all 10 provider-boundary tests, hybrid retrieval test, existing diagnostic, vendor scan, and configured Gradio HTTP startup passed.
- **No future Card leakage:** no typed agent-schema redesign, prompt/retrieval tuning, provider change, cloud integration, or V1-C04 implementation was added.

### CARD_QUALITY_GATE

**Status: PASS — ready for human review.**

- Focused tests: PASS — 8 bounded-loop/configuration tests.
- Relevant regression tests: PASS — 10 V1-C02 tests and 18 focused/regression tests total; `test/test1.py` exit code `0`.
- Card acceptance: PASS — every required success/failure/minimum/exhaustion path terminates deterministically with fake providers.
- Exit Gate fully mapped to evidence: YES.
- Evidence Map updated: YES.
- Diff/state/secrets/generated-artifact review: PASS — complete changed-file review, `git diff --check`, `git status`, credential-assignment scan, and generated-artifact check completed; the temporary Gradio artifacts were removed.
- Known limitations: verification routing still consumes the existing free-text report; V1-C04 owns typed contracts. Provider failures propagate truthfully and V1-C09 owns controlled fallback outcomes. The V1-C02 synthetic `NO_MATCH` retrieval observation was not tuned.
- Human approval required before V1-C04: YES.

## V1-C04 — Structured Agent Contracts
**Status:** READY FOR HUMAN REVIEW — Exit Gate and Card Quality Gate evidenced; no V1-C05 work started.

### Contract Map / Risk Map

- **Before:** the relevance agent returned labels such as `CAN_ANSWER`; research returned a loose dictionary; verification parsed line-oriented free text, rendered a Markdown report, and C03 routing searched that report for `**Supported:** NO` or `**Relevant:** NO`. Human display formatting and machine routing were therefore coupled.
- **Consumers/owners:** the provider boundary still exposes only `ChatProvider.generate()`. Each agent now owns parsing its own model output; `AgentState` owns typed per-run results and C03 retry/outcome state; `AgentWorkflow` owns deterministic routing; `app.py` continues to consume only `draft_answer` and `verification_report` for Gradio display.
- **Risk controlled:** a label typo, bolding change, prose explanation, or schema mismatch can no longer silently change a route. Strict Pydantic validation rejects undeclared/coerced/malformed JSON. Known structured-output errors reach explicit `FAILURE`, while unrelated provider failures still propagate rather than being hidden.

### Implementation / Typed Contracts

- `agents/contracts.py`: strict Pydantic contracts for `RelevanceResult`, `ResearchResult`, `VerificationResult`, and `TerminalOutcome`; `StructuredOutputError` names malformed model output explicitly.
- `RelevanceResult.decision` is a `RelevanceDecision` enum; `is_relevant` is derived deterministically. `ResearchResult` owns `draft_answer`. `VerificationResult` owns boolean `supported`/`relevant`, unsupported claims, contradictions, and correction feedback; `requires_research` derives retry control from booleans.
- `agents/relevance_checker.py`, `agents/research_agent.py`, and `agents/verification_agent.py`: request strict JSON and parse it at their boundary. The human report is rendered by `VerificationResult.to_human_report()` only after typed validation.
- `agents/workflow.py`: state now carries typed relevance/research/verification objects. Relevance routes on `result.is_relevant`; verification routes on `result.requires_research`; C03 `MAX_VERIFICATION_RETRIES`, retry counter, and `VERIFIED`/`OUT_OF_SCOPE`/`RETRY_EXHAUSTED` behavior are unchanged. A known `StructuredOutputError` produces an explicit `FAILURE` report and terminal route.
- `test/test_bounded_workflow.py` and `test/test_provider_boundary.py`: deterministic C03/C02 fakes now return the approved JSON contract rather than legacy text. `test/test_structured_contracts.py` adds C04 contract/routing coverage.

### Tests / Runtime

- `venv/bin/python -m unittest discover -s test -p 'test_structured_contracts.py' -v`: PASS — 6 focused tests. Proves typed partial-relevance routing, boolean verification retry/success, typed retry exhaustion, display-formatting independence, malformed verification JSON → `FAILURE`, and strict rejection instead of coercion.
- `venv/bin/python -m unittest discover -s test -p 'test_bounded_workflow.py' -v`: PASS — 8 V1-C03 bounded-loop/configuration tests.
- `venv/bin/python -m unittest discover -s test -p 'test_provider_boundary.py' -v`: PASS — 10 V1-C02 provider/configuration/hybrid-retrieval tests.
- `venv/bin/python -m unittest discover -s test -v`: PASS — 24 deterministic focused/regression tests total.
- `venv/bin/python test/test1.py`: PASS — exit code `0`; retained baseline parser diagnostic completed with known malformed PNG-as-PDF and Docling/Torch warnings.
- `venv/bin/python -m pip check`: PASS — `No broken requirements found`.
- `venv/bin/python -m compileall -q app.py agents config document_processor providers retriever test`: PASS.
- Active source/requirements Watsonx, LangChain IBM, LangChain OpenAI, IBM project/endpoint/model construction scan: PASS.
- Application integration: PASS — temporary `GRADIO_SERVER_PORT=7863` process bound `127.0.0.1:7863` and returned HTTP `200`; it was stopped cleanly. Generated `./.gradio/certificate.pem` and `./:memory:.ses` were inspected and removed.
- No Ollama model was downloaded. C04 structural behavior uses deterministic fakes; no prompt/retrieval-quality tuning was performed.

### Learning Record

**What we built / why:** Explicit Pydantic handoff contracts between three reasoning agents and the deterministic LangGraph coordinator. The old system treated a display string as an API; C04 makes the API machine-readable and keeps the display report separate.

**Architecture before → after:**

```text
Before: model text → ad hoc parser → Markdown report → string search → route
After:  model JSON → Pydantic result → typed workflow state → enum/boolean route
                         └──────────────────────────────→ human-readable report
```

**How communication now works:** Relevance produces an enum decision and explanation; research produces a typed draft; verification produces booleans, lists, and correction feedback. The workflow does not inspect `verification_report`: it checks `VerificationResult.requires_research`. The UI receives a report rendered from the validated result, so changing Markdown labels cannot alter control flow.

**Malformed-output behavior:** Invalid JSON, missing fields, extra fields, or incompatible types raise `StructuredOutputError`. The workflow catches that specific contract error, returns `FAILURE` with an understandable report, and terminates without spending retry budget or pretending verification succeeded. Provider failures are not swallowed.

**Professional engineering lesson:** Agent messages are interfaces, not just prose. Define a schema at the producer boundary, validate it before routing, and keep human presentation downstream. This makes routing testable with ordinary deterministic unit tests even when model output is probabilistic.

**Student takeaway:** In an agentic system, use the model for reasoning content but use typed state for program decisions. A sentence that looks like a status is not reliable control data; a validated boolean or enum is.

### Exit Gate Proof

- **No fragile free-text control parsing:** workflow routes from `RelevanceResult.is_relevant` and `VerificationResult.requires_research`; it contains no `Supported:`/`Relevant:` report-text predicate.
- **All required C03 terminal behavior remains:** boolean verification success → `VERIFIED`; typed failure obeys configured retry budget; exhausted budget → `RETRY_EXHAUSTED`; relevance rejection → `OUT_OF_SCOPE`.
- **Formatting cannot alter routing:** focused test includes misleading `**Supported:** NO` in human feedback while typed `supported=True` correctly ends `VERIFIED`.
- **Malformed output is explicit:** focused test proves malformed verification text reaches `FAILURE`, no retry, and no silent route.
- **V1-C02/C03 baseline preserved:** all 18 regression tests, hybrid retrieval, provider injection, configured Gradio HTTP startup, and active vendor-boundary scan passed.
- **No future Card leakage:** no citations/source IDs, retrieval evaluation, prompt-quality tuning, cloud provider, or V1-C05 implementation was added.

### CARD_QUALITY_GATE

**Status: PASS — ready for human review.**

- Focused tests: PASS — 6 typed-contract/routing tests.
- Relevant regression tests: PASS — 8 V1-C03 + 10 V1-C02 tests; 24 deterministic tests total; `test/test1.py` exit code `0`.
- Card acceptance: PASS — typed relevance/verification routing, bounded retry/exhaustion, formatting independence, and malformed structured output behavior are all demonstrated.
- Exit Gate fully mapped to evidence: YES.
- Evidence Map updated: YES.
- Diff/state/secrets/generated-artifact review: PASS — complete changed-file review, `git diff --check`, `git status`, credential-assignment scan, and generated-artifact check completed; temporary Gradio/test artifacts were removed.
- Known limitations: strict JSON compliance remains a model/runtime behavior to evaluate separately; C04 reports malformed output safely but does not add broader provider/retriever fallback policy (V1-C09). No source/citation work is present (V1-C05).
- Human approval required before V1-C05: YES.

## V1-C05 — Source & Citation Grounding
**Status:** READY FOR HUMAN REVIEW — Exit Gate and Card Quality Gate evidenced; no V1-C06 work started.

### Contract Map / Risk Map

- **Before:** Docling/header splitting produced chunks with incidental header metadata, but no stable document/chunk identity or normalized source metadata. Chroma/BM25 retrieved `Document` objects, research concatenated their text without identifiers, and neither workflow state nor Gradio exposed citations.
- **Ownership after:** `DocumentProcessor` owns deterministic local document/chunk provenance; `agents/citations.py` owns deterministic context labelling, resolution, and human display; `ResearchAgent` owns the model-proposed claim→chunk ID handoff; `AgentWorkflow` transports resolved citations without consuming them for control; `app.py` owns the minimal Sources & Citations display.
- **Trust boundary:** model-supplied chunk IDs are untrusted. The resolver matches them only against the current retrieved documents. Unknown or absent mappings become explicit unavailable citations; they never create a fabricated source, change relevance/verification routing, or spend a retry.
- **Metadata availability:** `document_id` is the existing file SHA-256; `chunk_id` is a SHA-256 of document ID, chunk position, and content; source name and Markdown section are attached at ingestion. Page is preserved only when a retrieved document already supplies integer `page` metadata; current Docling Markdown splitting does not invent page numbers.

### Implementation / Grounding Flow

```text
upload → file hash + Docling/header chunks → document_id/chunk_id/source/section metadata
       → Chroma + BM25 hybrid retrieval preserves metadata
       → labelled retrieved context → typed claim_sources from ResearchAgent
       → deterministic ID resolution → AgentState/full_pipeline → Gradio Sources & Citations
```

- `document_processor/file_handler.py:DocumentProcessor._attach_provenance()` attaches the same metadata after both fresh processing and cached loads, preserving the existing cache and deduplication behavior.
- `agents/contracts.py` extends `ResearchResult` with typed `ClaimSource` model handoffs and resolved `SourceCitation` records. Existing answer/control contracts remain intact.
- `agents/citations.py` labels only known retrieved chunk IDs for the research prompt, resolves those IDs against current evidence, and renders a user-facing report. No human-readable citation text is used as a workflow condition.
- `agents/research_agent.py` requests `claim_sources` alongside `draft_answer`; an empty mapping is allowed so unavailable citation evidence is visible rather than a crash.
- `agents/workflow.py` carries citations in typed workflow state and returns structured citation data plus a display report. C03 retry and terminal routing remain driven solely by typed relevance/verification state.
- `app.py` adds a minimal read-only Sources & Citations textbox; existing answer and verification outputs remain unchanged.
- `test/test_citation_grounding.py` adds deterministic local provenance/citation acceptance coverage.

### Tests / Runtime

- `venv/bin/python -m unittest discover -s test -p 'test_citation_grounding.py' -v`: PASS — 6 focused tests. Proves fresh+cached stable metadata, hybrid metadata preservation, valid claim→retrieved-source mapping, unknown-ID fallback, missing-mapping fallback, and no source invention.
- `venv/bin/python -m unittest discover -s test -p 'test_structured_contracts.py' -v`: PASS — 6 V1-C04 regression tests.
- `venv/bin/python -m unittest discover -s test -p 'test_bounded_workflow.py' -v`: PASS — 8 V1-C03 regression tests.
- `venv/bin/python -m unittest discover -s test -p 'test_provider_boundary.py' -v`: PASS — 10 V1-C02 provider/configuration/hybrid-retrieval regression tests.
- `venv/bin/python -m unittest discover -s test -v`: PASS — 30 deterministic tests total.
- `venv/bin/python test/test1.py`: PASS — exit code `0`; retained baseline Docling diagnostic completed with its known malformed PNG-as-PDF and Docling/Torch warnings.
- `venv/bin/python -m pip check`: PASS — `No broken requirements found`.
- `venv/bin/python -m compileall -q app.py agents config document_processor providers retriever test`: PASS.
- Active source/requirements IBM Watsonx, LangChain IBM, LangChain OpenAI, IBM endpoint/model scan: PASS — no active runtime coupling found.
- Gradio integration: PASS — temporary `GRADIO_SERVER_PORT=7864` process listened on `127.0.0.1:7864`; direct HTTP probe returned `200`; only that validation PID was terminated and generated `.gradio` artifacts were removed.
- A later repeat after marking the output field non-interactive did not reach HTTP-ready state within its process-management polling window and emitted no application error. The change is display-only, compilation passed afterward, and the earlier same-run HTTP-200 validation remains the application-startup evidence.
- No Ollama model was downloaded or invoked. C05 validation uses deterministic fake providers; no retrieval-quality tuning was performed.

### Learning Record

**What we built / why:** A local provenance chain that lets a reader inspect which retrieved document chunk a model associated with each important answer claim. Previously DocChat could retrieve evidence but could not expose that evidence as a stable source reference.

**How it works:**

1. The processor uses the existing file hash as a stable local document ID and derives a deterministic ID for each split chunk.
2. Chroma/BM25 returns those same metadata-bearing chunks. The Research Agent receives text labelled only with their real IDs and returns typed claim-to-ID mappings.
3. Deterministic code, not the model, resolves IDs against the retrieved set and prepares citations for the workflow and UI.
4. Unknown IDs or no mapping render an explicit unavailable-citation message. They do not invent attribution or influence verification/retry control.

**Architecture before → after:**

```text
Before: source file → anonymous chunk text → answer → no inspectable source
After:  source file → stable document/chunk metadata → retrieved labelled evidence
        → typed claim_sources → deterministic resolution → user-visible citations
```

**Professional engineering lesson:** Citation text is not provenance by itself. Reliable grounding needs an identity established before model generation, a constrained model reference, and deterministic validation after generation. Keeping that path separate from workflow control prevents an untrusted citation from changing program behavior.

**Student takeaway:** RAG is not automatically grounded because it retrieves text. Grounding becomes inspectable when the system can carry a source identity from ingestion through retrieval to the final answer. The LLM may propose a source, but deterministic code must verify that the source is actually present.

### Exit Gate Proof

- **Users can inspect where important claims came from:** valid mapping test produces a source name, section, page (when available), and stable chunk ID in `citation_report`; Gradio exposes that report in Sources & Citations.
- **Stable document/chunk identity and metadata:** fresh/cached processing test proves stable IDs, document ID, source name, and section; hybrid retrieval test proves metadata survives Chroma + BM25.
- **Claim-to-source mapping:** typed `ClaimSource` IDs are resolved only against the retrieved document set and returned as structured `citations`.
- **Graceful citation fallback:** unknown ID, empty ID list, and missing mapping tests show explicit unavailable messages without source fabrication or routing change.
- **Completed architecture preserved:** all 24 C02–C04 deterministic regressions pass; bounded terminal behavior and vendor-neutral Ollama/provider/hybrid-RAG architecture remain intact.
- **No future Card leakage:** no web provenance/freshness, retriever quality metric/tuning, advanced claim-level verification, cloud provider, or V1-C06 implementation was added.

### CARD_QUALITY_GATE

**Status: PASS — ready for human review.**

- Focused tests: PASS — 6 V1-C05 provenance/citation tests.
- Relevant regression tests: PASS — 6 V1-C04 + 8 V1-C03 + 10 V1-C02 tests; 30 deterministic tests total; retained `test/test1.py` exit code `0`.
- Card acceptance: PASS — metadata propagation, source mapping, unavailable-citation behavior, and user-display contract are all demonstrated.
- Exit Gate fully mapped to evidence: YES.
- Evidence Map updated: YES.
- Diff/state/secrets/generated-artifact review: PASS — only intended C05 files changed; `git diff --check`, `git status`, credential scan, C04 free-text-routing guard, and generated-artifact check passed; temporary Gradio and Python-cache artifacts were removed.
- Known limitations: current Docling Markdown chunks do not expose page numbers, so page is shown only if future/alternate retrieval metadata provides it; real models can return an empty `claim_sources` array, which is displayed as unavailable rather than treated as proof of grounding. Claim-level completeness/quality evaluation belongs to V1-C06/C07; web provenance/freshness belongs to V2.
- Human approval required before V1-C06: YES.

## V1-C06 — Retrieval Quality Evaluation
**Status:** READY FOR HUMAN REVIEW — Exit Gate and Card Quality Gate evidenced; no V1-C07 work started.

### Contract Map / Risk Map

- **Before:** `RetrieverBuilder` constructed BM25, Chroma vector retrieval, and a weighted `EnsembleRetriever`, but exposed only the production hybrid result. Existing tests proved the components could return documents, not whether they returned the expected C05 chunk evidence for known questions.
- **Evaluation identity:** C05 `chunk_id` is the only relevance identity used by this Card. Golden fixtures also carry `document_id`, source name, and section, but metrics compare expected/retrieved chunk IDs rather than generated answers, citation prose, verification reports, or model claims.
- **Fair comparison boundary:** the installed BM25 default is `k=4` while production vector retrieval uses `VECTOR_SEARCH_K`. C06 preserves the production hybrid constructor and adds `RetrieverBuilder.build_evaluation_modes(docs, k)`, which builds all three modes at the same explicit K.
- **Out-of-scope boundary:** a query with no gold evidence is recorded but excluded from Hit Rate@K and Recall@K denominators. Existing retrievers still return their top chunks without an abstention threshold; C06 measures that fact rather than treating arbitrary retrieval as a correct out-of-scope answer.

### Implementation / Evaluation Architecture

```text
golden source chunks + stable document_id/chunk_id
→ temporary Chroma + deterministic EmbeddingProvider fake
→ BM25-only | vector-only | weighted hybrid (common K=3)
→ retrieved chunk IDs ∩ expected chunk IDs
→ per-case results + Hit Rate@K + mean Recall@K
```

- `retriever/builder.py`: `RetrievalModes` and `build_evaluation_modes()` provide BM25/vector/hybrid comparators at one supplied K. `build_hybrid_retriever()` retains its existing production BM25 default and configured vector K behavior.
- `evaluation/retrieval_fixtures.py`: five controlled chunks across four source documents, each with stable C05-style IDs; four answerable/multi-document questions and one out-of-scope question. `DeterministicKeywordEmbedding` is a local test fake, not a production provider.
- `evaluation/retrieval_metrics.py`: validates fixture IDs, captures retrieved/matched IDs per case, computes Hit Rate@K and mean Recall@K only for answerable cases, and returns `None` rather than a fabricated score for an OOS-only evaluation.
- `evaluation/run_retrieval_evaluation.py`: reproducible command-line runner using temporary Chroma storage and `K=3`.
- `test/test_retrieval_evaluation.py`: fixture validation, unknown-ID rejection, deterministic ID matching, OOS denominator behavior, equal-K BM25/vector/hybrid evaluation, multi-document coverage, and repeatability.

### Measured Baseline

Run: `venv/bin/python -m evaluation.run_retrieval_evaluation`

| Mode | Scored cases | OOS cases | Hit Rate@3 | Mean Recall@3 | Multi-document case |
| --- | ---: | ---: | ---: | ---: | --- |
| BM25-only | 4 | 1 | 1.00 | 1.00 | both expected chunks found |
| Vector-only (deterministic fake) | 4 | 1 | 1.00 | 1.00 | both expected chunks found |
| Hybrid BM25 + vector | 4 | 1 | 1.00 | 1.00 | both expected chunks found |

The three modes tie on this deliberately small, controlled fixture. C06 therefore makes no claim that hybrid is better and makes no weight/K tuning change. The OOS geography case records no gold source and is unscored; each retriever still returned top chunks, demonstrating that retrieval evaluation is distinct from relevance/OOS routing.

### Tests / Runtime

- `venv/bin/python -m unittest discover -s test -p 'test_retrieval_evaluation.py' -v`: PASS — 6 focused C06 tests.
- `venv/bin/python -m evaluation.run_retrieval_evaluation`: PASS — repeatable BM25/vector/hybrid baseline reported above at common `K=3`.
- `venv/bin/python -m unittest discover -s test -p 'test_citation_grounding.py' -v`: PASS — 6 V1-C05 regression tests.
- `venv/bin/python -m unittest discover -s test -p 'test_structured_contracts.py' -v`: PASS — 6 V1-C04 regression tests.
- `venv/bin/python -m unittest discover -s test -p 'test_bounded_workflow.py' -v`: PASS — 8 V1-C03 regression tests.
- `venv/bin/python -m unittest discover -s test -p 'test_provider_boundary.py' -v`: PASS — 10 V1-C02 provider/configuration/hybrid-retrieval regression tests.
- `venv/bin/python -m unittest discover -s test -v`: PASS — 36 deterministic tests total.
- `venv/bin/python test/test1.py`: PASS — exit code `0`; retained Docling diagnostic has known malformed PNG-as-PDF and Docling/Torch warnings.
- `venv/bin/python -m pip check`: PASS — `No broken requirements found`.
- `venv/bin/python -m compileall -q app.py agents config document_processor providers retriever evaluation test`: PASS.
- Active source/requirements IBM Watsonx, LangChain IBM, LangChain OpenAI, IBM endpoint/model scan: PASS — no active runtime coupling found.
- No Ollama model was downloaded or invoked. Chroma telemetry emitted known non-blocking `capture()` warnings during temporary evaluation stores.

### Learning Record

**What we built / why:** A repeatable golden retrieval evaluation that asks a narrow question: did each retriever return the expected evidence chunks? It deliberately does not ask whether a model wrote a good answer.

**How it works:**

1. Version-controlled fixtures define controlled source chunks and their stable C05 IDs.
2. Each question declares its expected relevant chunk IDs; a multi-document query expects two IDs and an OOS query expects none.
3. BM25, vector, and hybrid run with the same K against temporary storage.
4. Deterministic metrics compare retrieved IDs with expected IDs. Hit Rate@K means at least one expected chunk appeared in the first K; Recall@K means the fraction of all expected chunks that appeared in the first K.
5. Answer text and verification never enter the calculation, so retrieval quality remains an independently testable property.

**Architecture before → after:**

```text
Before: hybrid retrieval exists → answer looks plausible → retrieval quality assumed
After:  golden question → expected C05 chunk IDs → mode-specific retrieved IDs
        → repeatable Hit Rate@K / Recall@K evidence
```

**Professional engineering lesson:** Evaluation needs a fixed truth set and a stable identity boundary. Compare identical inputs and K across modes, record ties as ties, and do not tune parameters until a baseline measurement exists. Retrieval quality, answer quality, and verification quality are separate measurements with different failure causes.

**Student takeaway:** A good-looking RAG answer can hide a retrieval failure. Golden retrieval evaluation checks the step before generation: whether the right evidence arrived. Only then can later Cards evaluate whether the answer used that evidence faithfully.

### Exit Gate Proof

- **Retrieval quality is measured, not assumed:** reproducible runner and 6 focused tests produce per-case ID overlap, Hit Rate@3, and Recall@3 for all three modes.
- **Known evidence is comparable:** fixtures validate unique stable chunk IDs; expected IDs must exist in controlled source documents; unknown IDs fail validation.
- **BM25/vector/hybrid comparison is fair:** all modes are built at the same explicit `K=3`, verified by test, and measured from the same five chunks/five questions.
- **Multi-document and OOS are represented:** the multi-document case expects/retrieves both source chunks; the no-gold OOS case is retained but excluded from metrics rather than falsely passing.
- **Completed architecture preserved:** all 30 C02–C05 regression tests pass; production hybrid construction, provider abstraction, bounded workflow, typed contracts, and citation grounding remain unchanged.
- **No future Card leakage:** no retrieval tuning, answer/verification evaluation, prompt change, cloud provider, observability, or V1-C07 implementation was added.

### CARD_QUALITY_GATE

**Status: PASS — ready for human review.**

- Focused tests: PASS — 6 V1-C06 fixture/metric/mode/repeatability tests.
- Relevant regression tests: PASS — 6 V1-C05 + 6 V1-C04 + 8 V1-C03 + 10 V1-C02 tests; 36 deterministic tests total; retained `test/test1.py` exit code `0`.
- Card acceptance: PASS — golden dataset validation and all three common-K measurements executed with recorded results.
- Exit Gate fully mapped to evidence: YES.
- Evidence Map updated: YES.
- Diff/state/secrets/generated-artifact review: PASS — only intended C06 evaluation, retriever-boundary, focused-test, and evidence files changed; `git diff --check`, `git status`, credential scan, and generated-artifact/temporary-Chroma check passed.
- Known limitations: five controlled chunks are a foundation, not a representative corpus; deterministic fake vectors do not measure real Ollama embedding quality; OOS is unscored and does not add a retrieval abstention threshold. Claim/answer/verification quality is deferred to V1-C07.
- Human approval required before V1-C07: YES.

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
