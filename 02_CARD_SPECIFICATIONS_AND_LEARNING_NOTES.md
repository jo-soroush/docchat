# DocChat Card Specifications & Learning Notes

## Purpose

This file is the detailed engineering/learning companion to `01_DOCCHAT_ROADMAP.md`.

The roadmap defines official Card identity, order, goals, and Exit Gates. This file records the complete working contract for each Card. Repository evidence must be inspected before implementation.

## Required 14-Section Card Contract

Every active Card must contain:

1. Title
2. Engineering Goal
3. Learning Goal
4. Why It Exists
5. Architecture Concept
6. Current System Before Card
7. Design Decision
8. Implementation Scope
9. Out of Scope
10. Dependencies
11. Tests / Evaluation
12. Exit Gate
13. What We Learned
14. Completion Evidence

Sections 1–12 are pre-implementation contract.
Sections 13–14 are filled only from actual implementation/evidence.

---

# V1 Cards

## V1-C01 — Baseline Preservation & Architecture Audit

### 1. Title
Baseline Preservation & Architecture Audit

### 2. Engineering Goal
Document the selected IBM DocChat baseline, reusable capabilities, vendor coupling, and the approved independent target architecture before migration implementation.

### 3. Learning Goal
Understand which baseline responsibilities are reusable core behavior and which are IBM-specific provider coupling.

### 4. Why It Exists
All later Cards depend on knowing repository reality, preserving useful behavior, and separating historical provenance from runtime dependency.

### 5. Architecture Concept
Evidence-first architecture discovery, coupling analysis, and migration planning.

### 6. Current System Before Card
Selected baseline is the IBM final-lab implementation on the project baseline branch. Custom DocChat extensions have not started. Exact runtime behavior must be verified from repository evidence.

### 7. Design Decision
Do not migrate providers during this Card. Inspect, map, test where feasible, record provenance/limitations, and establish the authoritative `DocChat Core → Provider Abstraction → Local / Cloud Providers` target for V1-C02.

### 8. Implementation Scope
- verify Git/baseline state;
- inspect repository ownership and dependencies;
- trace upload/query → processing → retrieval → relevance → research → verification → routing → final/UI;
- map LangGraph state/nodes/edges/loops/termination;
- map Research/Verification responsibilities and contracts;
- inspect Docling/chunk/cache/embedding/Chroma/BM25/vector/hybrid behavior;
- inspect validation/tests;
- create architecture/dependency/preservation/risk maps;
- record provenance/license concerns;
- establish baseline test questions and known limitations.
- classify reusable core, configuration-only coupling, and IBM architectural coupling;
- record the project-owner local-first/Ollama architecture decision and revised Card order.

### 9. Out of Scope
- no custom feature implementation;
- no provider abstraction or Ollama implementation;
- no UI rewrite;
- no new agents;
- no V2 behavior;
- no cleanup/refactor merely for style.

### 10. Dependencies
None beyond a valid repository/runtime environment and selected IBM baseline.

### 11. Tests / Evaluation
Run existing tests where feasible, execute baseline application/critical paths, record actual failures/blockers, and establish reproducible baseline checks.

### 12. Exit Gate
Baseline runtime blockers are precisely evidenced; repository architecture, provenance, and vendor-coupling map are documented; the independent target architecture and bounded V1-C02 migration contract are approved and ready for human review.

### 13. What We Learned
`Pending — fill only after audit evidence exists.`

### 14. Completion Evidence
`Pending — fill only after Exit Gate proof exists.`

---

## V1-C02 — Provider Boundary & Ollama Local Runtime
1. **Title:** Provider Boundary & Ollama Local Runtime
2. **Engineering Goal:** Make the active DocChat runtime independent of IBM Watsonx by introducing a narrow provider boundary and its first local Ollama implementation.
3. **Learning Goal:** Learn how to isolate vendor-specific inference/embedding behavior while preserving RAG and workflow ownership.
4. **Why It Exists:** The historical baseline cannot run independently because chat and embeddings are coupled to IBM credentials, project IDs, SDKs, and hosted models.
5. **Architecture Concept:** `DocChat Core → Provider Abstraction → Local / Cloud Providers`.
6. **Current System Before Card:** V1-C01 records direct Watsonx use in three agents and the retriever builder; document processing, retrieval composition, workflow, and UI are reusable.
7. **Design Decision:** Ollama is the first local provider. Core imports no Watsonx/OpenAI/AWS SDK. Future cloud providers implement the same explicit contracts.
8. **Implementation Scope:** chat and embedding contracts; Ollama adapters; local configuration; deterministic fakes; migration of current Watsonx call sites; removal of active IBM runtime dependencies; parity/regression tests for retained behavior.
9. **Out of Scope:** a generic provider marketplace, concrete cloud adapters, V2 tools/source routing, workflow redesign, and feature expansion.
10. **Dependencies:** V1-C01 closed with this architecture decision.
11. **Tests / Evaluation:** contract tests with fakes; Ollama availability/failure tests; local document→retrieval→workflow smoke path; regression tests for retained core behavior.
12. **Exit Gate:** A local Ollama configuration runs the DocChat core path without IBM credentials, IBM projects, IBM SDK imports, or IBM runtime services.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C03 — Bounded Research / Verification Loop
1. **Title:** Bounded Research / Verification Loop
2. **Engineering Goal:** Guarantee termination of the existing correction loop.
3. **Learning Goal:** Understand deterministic termination around probabilistic agents.
4. **Why It Exists:** Unbounded agent loops are unsafe and operationally unreliable.
5. **Architecture Concept:** Explicit retry state + deterministic terminal routing.
6. **Current System Before Card:** Populate from V1-C01/V1-C02 evidence.
7. **Design Decision:** Preserve Research + Verification + re-research; add bounded control.
8. **Implementation Scope:** retry counter/limit, explicit terminal outcomes, deterministic routes, path tests.
9. **Out of Scope:** broader schema redesign except minimal boundary required; V2 Reflexion/ReAct.
10. **Dependencies:** V1-C02.
11. **Tests / Evaluation:** all terminal paths, retry exhaustion, out-of-scope, success/failure.
12. **Exit Gate:** No query can enter an unbounded research/verification loop.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C04 — Structured Agent Contracts
1. **Title:** Structured Agent Contracts
2. **Engineering Goal:** Replace fragile free-text control parsing with typed schemas.
3. **Learning Goal:** Understand explicit contracts between agent/workflow stages.
4. **Why It Exists:** Free-text control signals are fragile and difficult to validate.
5. **Architecture Concept:** Typed structured outputs/state.
6. **Current System Before Card:** Populate from prior evidence.
7. **Design Decision:** Introduce schemas at existing ownership boundaries.
8. **Implementation Scope:** relevance, research, verification, unsupported claims, contradictions, correction feedback, terminal state.
9. **Out of Scope:** new specialist agents or V2 tool orchestration.
10. **Dependencies:** V1-C03.
11. **Tests / Evaluation:** valid/malformed outputs, schema invariants, routing integration.
12. **Exit Gate:** Control flow no longer depends on parsing strings such as `Supported: NO`.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C05 — Source & Citation Grounding
1. **Title:** Source & Citation Grounding
2. **Engineering Goal:** Make important claims traceable to source evidence.
3. **Learning Goal:** Understand provenance across ingestion, retrieval, generation, and verification.
4. **Why It Exists:** Grounded research requires inspectable evidence.
5. **Architecture Concept:** Stable document/chunk identity and claim/source trace.
6. **Current System Before Card:** Populate from evidence.
7. **Design Decision:** Extend metadata/contracts without breaking retrieval.
8. **Implementation Scope:** document/chunk IDs, page/section metadata, citations, claim-source mapping, graceful fallback.
9. **Out of Scope:** V2 web provenance/freshness system.
10. **Dependencies:** V1-C04.
11. **Tests / Evaluation:** metadata propagation, citation mapping, unavailable-citation behavior.
12. **Exit Gate:** Users can inspect where important claims came from.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C06 — Retrieval Quality Evaluation
1. **Title:** Retrieval Quality Evaluation
2. **Engineering Goal:** Quantitatively evaluate retrieval.
3. **Learning Goal:** Learn why retrieval quality must be measured separately from generation.
4. **Why It Exists:** Good-looking answers cannot prove retriever quality.
5. **Architecture Concept:** Golden retrieval fixtures and comparative metrics.
6. **Current System Before Card:** Populate from evidence.
7. **Design Decision:** Preserve BM25/vector/hybrid and compare them.
8. **Implementation Scope:** fixed docs, question→passage fixtures, Recall@K/hit-rate, retriever comparisons, multi-doc/OOS cases.
9. **Out of Scope:** V2 production monitoring.
10. **Dependencies:** V1-C05.
11. **Tests / Evaluation:** deterministic retrieval evaluation suite.
12. **Exit Gate:** Retrieval quality is measured, not assumed.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C07 — Answer & Verification Evaluation Suite
1. **Title:** Answer & Verification Evaluation Suite
2. **Engineering Goal:** Detect regressions in grounded answer/verification behavior.
3. **Learning Goal:** Separate retrieval success from answer support and verification quality.
4. **Why It Exists:** Agent quality needs repeatable behavioral evidence.
5. **Architecture Concept:** Golden cases across support/failure/correction.
6. **Current System Before Card:** Populate from evidence.
7. **Design Decision:** Evaluate representative behavior, including failure paths.
8. **Implementation Scope:** answerable/partial/OOS/numerical/unsupported/contradiction/multi-chunk/multi-doc/correction/retry cases.
9. **Out of Scope:** large-scale V2 monitoring.
10. **Dependencies:** V1-C06.
11. **Tests / Evaluation:** repeatable answer + verification suite.
12. **Exit Gate:** Suite detects regressions in retrieval and grounded answer quality.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C08 — Observability & Run Trace
1. **Title:** Observability & Run Trace
2. **Engineering Goal:** Make each query diagnosable.
3. **Learning Goal:** Understand observability across agentic workflows.
4. **Why It Exists:** Failures must be attributable to the correct boundary.
5. **Architecture Concept:** Safe structured run trace.
6. **Current System Before Card:** Populate from evidence.
7. **Design Decision:** Trace decisions/evidence without leaking sensitive content.
8. **Implementation Scope:** run ID, retrieved IDs, decisions, attempts, verification, route, latency, terminal result, safe errors.
9. **Out of Scope:** full production telemetry platform.
10. **Dependencies:** V1-C07.
11. **Tests / Evaluation:** trace completeness and safe-error behavior.
12. **Exit Gate:** Poor results can be localized to the responsible stage.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C09 — Robust Error Handling & Fallbacks
1. **Title:** Robust Error Handling & Fallbacks
2. **Engineering Goal:** Convert known failures into controlled outcomes.
3. **Learning Goal:** Design failure contracts around external/model/retrieval dependencies.
4. **Why It Exists:** Agentic systems must fail explicitly and safely.
5. **Architecture Concept:** Typed/controlled failure paths.
6. **Current System Before Card:** Populate from evidence.
7. **Design Decision:** Handle known failures at their owning boundary.
8. **Implementation Scope:** parse/file/retriever/embedding/model/malformed-output/zero-doc/verification/cache/partial-file failures.
9. **Out of Scope:** unrelated infrastructure resilience.
10. **Dependencies:** V1-C08.
11. **Tests / Evaluation:** focused failure injection and controlled outcomes.
12. **Exit Gate:** Known failures produce explicit safe outcomes and tests.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C10 — Research Assistant Product Experience
1. **Title:** Research Assistant Product Experience
2. **Engineering Goal:** Improve study/research operations while preserving the verified backend.
3. **Learning Goal:** Keep UI/product concerns separate from core AI architecture.
4. **Why It Exists:** Reliable backend capability must become useful to a researcher/student.
5. **Architecture Concept:** Thin product/UI adapter over verified workflows.
6. **Current System Before Card:** Populate from evidence.
7. **Design Decision:** Keep Gradio baseline for V1; add operations without moving core logic into UI.
8. **Implementation Scope:** Ask, Summarize, Key Points, Compare Sources, Explain Concept, Study Questions.
9. **Out of Scope:** permanent production UI decision.
10. **Dependencies:** V1-C09.
11. **Tests / Evaluation:** operation routing and backend behavior preservation.
12. **Exit Gate:** Users can study books/papers through the same verified backend.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

## V1-C11 — V1 Closure & Portfolio Evidence
1. **Title:** V1 Closure & Portfolio Evidence
2. **Engineering Goal:** Make V1 reproducible, explainable, and demonstrable.
3. **Learning Goal:** Practice professional project closure and evidence communication.
4. **Why It Exists:** A portfolio/company-style project must be reproducible and auditable.
5. **Architecture Concept:** Documentation/evidence as part of engineering quality.
6. **Current System Before Card:** Populate from evidence.
7. **Design Decision:** Close only from verified repository state.
8. **Implementation Scope:** architecture diagram, setup, provenance, decisions, baseline-vs-extension, evaluations, limitations, demos, learning notes.
9. **Out of Scope:** V2 implementation.
10. **Dependencies:** V1-C10 and all V1 Exit Gates.
11. **Tests / Evaluation:** clean setup/run/test reproduction and evidence review.
12. **Exit Gate:** A new developer can clone, run, test, understand, and explain the system.
13. **What We Learned:** Pending.
14. **Completion Evidence:** Pending.

---

# V2 Cards

For V2, Sections 6, 13, and 14 remain evidence-driven and must be completed only when the Card becomes active.

## V2-C01 — Agentic Source Router
**Engineering Goal:** Structured, testable, permission-bounded source selection.
**Learning Goal:** Learn agentic RAG source selection without searching everything.
**Scope:** uploaded docs, persistent library, web/external approved sources, safe no-source result.
**Dependencies:** V1 closed.
**Exit Gate:** Source selection is structured, testable, permission-bounded, and can safely return no-supported-source.

## V2-C02 — Research Tool Registry
**Engineering Goal:** Controlled typed research tools.
**Learning Goal:** Understand tool boundaries, permissions, timeout, and failure contracts.
**Scope:** registered retrieval/search/metadata/calculator/citation tools as approved.
**Dependencies:** V2-C01.
**Exit Gate:** Only registered authorized tools can be called.

## V2-C03 — ReAct Research Agent
**Engineering Goal:** Bounded dynamic tool selection.
**Learning Goal:** Implement Reason→Act→Observe safely.
**Scope:** tool budget/history, STOP rules, bounded execution.
**Dependencies:** V2-C02.
**Exit Gate:** Adaptive multi-step research always terminates safely.

## V2-C04 — Reflexion with External Evidence
**Engineering Goal:** Retrieve missing evidence and revise weak answers.
**Learning Goal:** Distinguish reflection from evidence-seeking Reflexion.
**Scope:** missing-evidence schema, queries, freshness/relevance, revisor, bounded loop.
**Dependencies:** V2-C03.
**Exit Gate:** Unsupported answers can improve with new evidence without unbounded search.

## V2-C05 — Specialized Multi-Agent Boundaries
**Engineering Goal:** Add specialists only where measurable value exists.
**Learning Goal:** Learn justified agent decomposition.
**Scope:** candidate Research, Verification, Critique/Risk, Synthesis agents.
**Dependencies:** prior V2 evidence.
**Exit Gate:** Every agent has a clear boundary, typed handoff, dedicated prompt/tools, and measurable reason.

## V2-C06 — Coordinator / Supervisor Routing
**Engineering Goal:** Coordinate specialist agents safely.
**Learning Goal:** Learn hub-and-spoke/sequential/parallel orchestration.
**Scope:** assignment, handoffs, selective parallelism, aggregation, fallback.
**Dependencies:** V2-C05.
**Exit Gate:** Supported tasks route correctly with deterministic terminal behavior.

## V2-C07 — Advanced Grounded Verification
**Engineering Goal:** Claim-level verification.
**Learning Goal:** Learn evidence status per claim.
**Scope:** claim extraction/mapping, citation consistency, contradiction, freshness/provenance, UNKNOWN/INSUFFICIENT_EVIDENCE.
**Dependencies:** V2-C06.
**Exit Gate:** Important claims are individually supported, contradicted, or unknown.

## V2-C08 — Human-in-the-Loop Review
**Engineering Goal:** Pause/resume around human judgment.
**Learning Goal:** Learn where autonomy should stop.
**Scope:** review triggers, approval state, resume behavior.
**Dependencies:** V2-C07.
**Exit Gate:** Required approval cannot be bypassed.

## V2-C09 — Permissions, Privacy & Security Guardrails
**Engineering Goal:** Least-privilege agent/tool/document security.
**Learning Goal:** Treat external content/tools as security boundaries.
**Scope:** permissions, document boundaries, secrets, injection defense, untrusted docs, redacted logs, file controls.
**Dependencies:** relevant V2 tool/source architecture.
**Exit Gate:** Unauthorized access is prevented and security rules have tests.

## V2-C10 — Persistent Research Collections & Memory Boundary
**Engineering Goal:** Reusable personal research libraries with explicit memory separation.
**Learning Goal:** Distinguish persistence, retrieval context, workflow state, checkpoints, and memory.
**Scope:** named collections, metadata, session references, explicit boundaries.
**Dependencies:** V2 source/retrieval architecture.
**Exit Gate:** Collections persist safely without silently becoming agent memory.

## V2-C11 — Production Evaluation & Monitoring
**Engineering Goal:** Quantitatively compare system versions/behavior.
**Learning Goal:** Learn continuous evaluation for agentic systems.
**Scope:** golden dataset, retrieval/groundedness/citation/unsupported-claim/retry/tool/latency/failure metrics, version comparison.
**Dependencies:** implemented V2 behavior.
**Exit Gate:** Relevant changes can be quantitatively compared before release.

## V2-C12 — Deployment & Multi-User Boundary
**Engineering Goal:** Prepare controlled real-world multi-user operation.
**Learning Goal:** Understand deployment boundaries beyond local prototypes.
**Scope:** authn/authz, user isolation, persistent DB, deployment config, backups, health, rate limiting, monitoring, secrets as needed.
**Dependencies:** V2 architecture/evaluation/security.
**Exit Gate:** Multiple authorized users can use the deployed system without data leakage or verification bypass.

## Provider Strategy Note

The exact DocChat model/provider strategy remains an explicit design decision to resolve from repository evidence. Preferred direction is local-first with Ollama while preserving replaceability for cloud APIs and AWS/cloud-hosted endpoints. Do not implement this merely because it appears here; activate it only through an approved Card decision.
