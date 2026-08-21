# DocChat V1 & V2 Engineering Roadmap

## Authority

This roadmap formalizes the approved DocChat direction. Repository reality and verified evidence remain authoritative for implementation state. The IBM baseline must be preserved before extensions are introduced.

## Project Principle

Extend the original IBM Skills Network DocChat; do not reduce useful baseline capability for convenience.

## V1 — Reliable Personal Research Assistant

### C01 — Baseline Preservation & Architecture Audit
**Goal:** Run and document the real IBM baseline before changing it.
**Add:** architecture map, dependency map, baseline test questions, known limitations, license/provenance record.
**Exit Gate:** Original application runs and repository architecture is documented from evidence.

### C02 — Bounded Research / Verification Loop
**Goal:** Guarantee termination of the existing correction loop.
**Keep:** Research Agent, Verification Agent, re-research on verification failure.
**Add:** retry counter/limit; VERIFIED, OUT_OF_SCOPE, RETRY_EXHAUSTED, FAILURE outcomes; deterministic routing; path tests.
**Exit Gate:** No query can enter an unbounded research/verification loop.

### C03 — Structured Agent Contracts
**Goal:** Replace fragile free-text parsing with typed schemas.
**Add:** schemas for relevance, research result, verification result, unsupported claims, contradictions, correction feedback, terminal state.
**Exit Gate:** Control flow no longer depends on parsing strings such as `Supported: NO`.

### C04 — Source & Citation Grounding
**Goal:** Make important factual claims traceable.
**Add:** document/chunk identity, page/section metadata where available, citations, claim-to-source mapping, graceful citation fallback.
**Exit Gate:** Users can inspect where important claims came from.

### C05 — Retrieval Quality Evaluation
**Goal:** Measure retrieval quality.
**Keep:** BM25, vector search, hybrid ensemble.
**Add:** fixed evaluation documents, question→passage fixtures, Recall@K/hit-rate checks, retriever comparisons, multi-document and out-of-scope tests.
**Exit Gate:** Retrieval quality is measured, not assumed.

### C06 — Answer & Verification Evaluation Suite
**Goal:** Measure support, hallucination, relevance, and correction.
**Add:** answerable, partial, out-of-scope, numerical-error, unsupported-claim, contradiction, multi-chunk, multi-document, correction-success, retry-exhaustion cases.
**Exit Gate:** A repeatable suite detects regressions in retrieval and grounded answer quality.

### C07 — Observability & Run Trace
**Goal:** Make each query diagnosable.
**Add:** run ID, retrieved IDs, relevance decision, attempt number, verification result, route, latency, terminal result, safe errors.
**Exit Gate:** Poor results can be localized to retrieval, relevance, generation, verification, routing, or infrastructure.

### C08 — Robust Error Handling & Fallbacks
**Goal:** Convert known failures into controlled outcomes.
**Handle:** parse/empty/unsupported files, embedding/retriever failures, model timeout, malformed structured output, zero docs, verification/cache failures, partial multi-file processing.
**Exit Gate:** Known failures produce explicit safe outcomes and tests.

### C09 — Research Assistant Product Experience
**Goal:** Keep Gradio while improving personal research/study usefulness.
**Keep:** upload, question, answer, verification report, session reuse.
**Add:** Ask, Summarize, Key Points, Compare Sources, Explain Concept, Generate Study Questions.
**Exit Gate:** Users can study books/papers through the same verified backend workflow.

### C10 — V1 Closure & Portfolio Evidence
**Goal:** Close V1 as a reproducible final project.
**Add:** architecture diagram, setup guide, provenance/license, design decisions, baseline-vs-extension record, evaluation results, limitations, verified demos, learning notes.
**Exit Gate:** A new developer can clone, run, test, understand, and explain the system.

## V2 — Agentic Research Intelligence System

V2 adds capabilities; it does not replace V1 foundations.

### C01 — Agentic Source Router
**Goal:** Select the appropriate source/retrieval path.
**Sources:** uploaded docs, persistent library, public web, trusted external knowledge service, future domain APIs.
**Exit Gate:** Selection is structured, testable, permission-bounded, and can safely return no-supported-source.

### C02 — Research Tool Registry
**Goal:** Give research a controlled tool set.
**Tools:** document retrieval, web/news search, metadata lookup, calculator, citation resolver, future domain tools.
**Exit Gate:** Only registered authorized tools can be called; each has typed I/O, permissions, timeout, and failure contract.

### C03 — ReAct Research Agent
**Goal:** Let research dynamically select the next tool.
**Pattern:** Reason → Select Tool → Act → Observe → Reason Again → Enough Evidence?
**Add:** tool-call budget/history, STOP rules, bounded execution.
**Exit Gate:** Multi-step research adapts dynamically and always terminates safely.

### C04 — Reflexion with External Evidence
**Goal:** Let weak answers identify and retrieve missing evidence, revise, and reverify.
**Add:** missing-evidence schema, research queries, freshness/relevance checks, revisor contract, bounded reflexion.
**Exit Gate:** Unsupported answers can improve using new evidence without unbounded search.

### C05 — Specialized Multi-Agent Boundaries
**Goal:** Split responsibilities only where specialization adds measurable value.
**Candidates:** Research, Verification/Fact-Checking, Critique/Risk, Report/Synthesis.
**Exit Gate:** Every agent has a clear boundary, typed handoff, dedicated prompt/tools, and measurable reason to exist.

### C06 — Coordinator / Supervisor Routing
**Goal:** Coordinate specialist agents.
**Add:** structured assignment, handoff rules, selective sequential/parallel work, aggregation, failure/fallback routing.
**Exit Gate:** Supported tasks route correctly with deterministic terminal behavior.

### C07 — Advanced Grounded Verification
**Goal:** Move to claim-level checking.
**Add:** claim extraction, claim→source mapping, citation consistency, cross-source contradiction detection, freshness/provenance, UNKNOWN/INSUFFICIENT_EVIDENCE.
**Exit Gate:** Important claims are individually supported, contradicted, or marked unknown.

### C08 — Human-in-the-Loop Review
**Goal:** Pause when human judgment is required.
**Triggers:** conflicting sources, low support, repeated verification failure, sensitive/high-stakes use, future consequential action.
**Exit Gate:** Pause/review/resume works and required approval cannot be bypassed.

### C09 — Permissions, Privacy & Security Guardrails
**Goal:** Apply least privilege.
**Add:** tool permissions, document boundaries, secret management, prompt-injection defenses, untrusted-document handling, redacted logging, file controls.
**Exit Gate:** Unauthorized tool/data access is prevented and security rules have tests.

### C10 — Persistent Research Collections & Memory Boundary
**Goal:** Support reusable research libraries without confusing them with agent memory.
**Add:** named collections, persistent metadata, session references, separation of source docs/retrieved context/workflow state/checkpoints/long-term memory.
**Exit Gate:** Collections persist safely without silently becoming agent memory.

### C11 — Production Evaluation & Monitoring
**Goal:** Continuously measure behavior.
**Add:** larger golden dataset, retrieval metrics, groundedness, citation accuracy, unsupported-claim rate, retry/tool-call frequency, latency/failure rates, model/prompt/retriever comparisons.
**Exit Gate:** Relevant changes can be quantitatively compared before release.

### C12 — Deployment & Multi-User Boundary
**Goal:** Prepare for controlled real-world use.
**Add as needed:** authn/authz, per-user document isolation, persistent DB, deployment config, backups, health checks, rate limiting, monitoring, secure secrets.
**Exit Gate:** Multiple authorized users can use the deployed system without data leakage or verification bypass.

## Cross-Project Provider Principle

Prefer local-first development while preserving replaceable model/provider boundaries. Ollama may be the preferred local runtime, but provider portability must be introduced only when justified by repository evidence and an approved Card. Target portability includes local models, cloud APIs, and cloud/AWS-hosted endpoints.

## Non-Goals

Do not equate V2 with making every step an agent, searching every source, unlimited autonomous research, unlimited agent conversations, removing deterministic validation, automatic self-learning, or unrestricted external actions.

## Guiding Principle

Use deterministic software for deterministic responsibilities. Use agents only where autonomous reasoning, source selection, research, critique, or synthesis adds measurable value.
