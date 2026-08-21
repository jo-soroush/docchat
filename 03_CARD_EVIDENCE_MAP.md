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

---

# V1 Evidence

## V1-C01 — Baseline Preservation & Architecture Audit

**Status:** NOT STARTED / VERIFY CURRENT STATE

### Implementation / Inspection
- Repository/file ownership map: Pending
- End-to-end contract map: Pending
- LangGraph state/nodes/edges/routes/loops/termination: Pending
- Research Agent contract: Pending
- Verification Agent contract: Pending
- document processing/chunk/cache map: Pending
- embeddings/ChromaDB map: Pending
- BM25/vector/hybrid retrieval map: Pending
- UI/application/session reuse map: Pending
- preservation map: Pending
- dependency map: Pending
- risk map: Pending
- provenance/license record: Pending
- known limitations: Pending

### Tests / Runtime
- Existing tests discovered: Pending
- Existing tests executed: Pending
- Baseline application run: Pending
- Baseline test questions: Pending
- Actual results: Pending

### Git / Repository
- Current branch verified: Pending
- Tracking/upstream verified: Pending
- Working tree verified: Pending
- Baseline commit verified: Pending

### Exit Gate
**Pending.** Original application must run (or blockers be precisely evidenced) and repository architecture must be documented from evidence.

### Remaining
Run the approved inspect-only V1-C01 audit before any custom implementation.

---

## V1-C02 — Bounded Research / Verification Loop
**Status:** BLOCKED — depends on V1-C01 closure.
**Evidence:** Pending.

## V1-C03 — Structured Agent Contracts
**Status:** BLOCKED — dependency chain not satisfied.
**Evidence:** Pending.

## V1-C04 — Source & Citation Grounding
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C05 — Retrieval Quality Evaluation
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C06 — Answer & Verification Evaluation Suite
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C07 — Observability & Run Trace
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C08 — Robust Error Handling & Fallbacks
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C09 — Research Assistant Product Experience
**Status:** BLOCKED.
**Evidence:** Pending.

## V1-C10 — V1 Closure & Portfolio Evidence
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
