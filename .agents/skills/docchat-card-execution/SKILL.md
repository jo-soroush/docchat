---
name: docchat-card-execution
description: Execute one DocChat V1/V2 Card safely and educationally using the roadmap, repository reality, baseline-preservation rules, validation, and verified evidence.
---

# DocChat Card Execution Skill

## Purpose

This skill defines the operational procedure for executing one DocChat Card.

It does not redefine project architecture, roadmap scope, or IBM baseline behavior.

Always obey `AGENTS.md`.

## Phase 1 — Resolve the Active Card

Read the approved roadmap and resolve the official Active Card.

Read its complete contract/specification and existing evidence when available.

Inspect current Git/repository state.

Confirm:
- title;
- Engineering Goal;
- why it exists;
- current system before the Card;
- design decision;
- implementation scope;
- out of scope;
- dependencies;
- tests/evaluation;
- Exit Gate.

Do not proceed from chat memory when repository authorities are available.

## Phase 2 — Reconcile Repository Reality

Inspect current source, tests, configuration, dependencies, and relevant Git history.

Compare repository reality with the Card assumptions and IBM baseline.

If repository evidence disproves an assumption:
1. identify the mismatch;
2. explain its impact;
3. stop before changing architecture;
4. resolve the discrepancy explicitly.

Never invent repository state.

## Phase 3 — Inspect-Only Contract Map / Risk Map

For the first implementation step of a new Card, do not write code.

Trace the complete relevant path.

Typical DocChat path:

```text
User upload/query
→ parsing / validation / cache
→ chunking + metadata
→ embeddings / vector store
→ BM25 + vector retrieval
→ hybrid retriever
→ relevance decision
→ Research Agent
→ structured draft/evidence
→ Verification Agent
→ route / bounded re-research
→ terminal result
→ application/UI output
```

### Contract Map

Identify:
- entry points;
- producers/providers;
- state/data schemas;
- document/chunk identities and metadata;
- retrieval ownership;
- model/provider boundaries;
- agent inputs/outputs;
- routing contracts;
- consumers;
- final outputs;
- tests/evaluation covering the path.

### Risk Map

Identify:
- missing/fragile contracts;
- free-text parsing dependencies;
- duplicate ownership;
- hidden dependencies;
- incompatible data/state shapes;
- unbounded loops;
- malformed model output;
- retrieval/embedding/model failures;
- unsupported claims/hallucination risks;
- citation/provenance gaps;
- cache/pickle/security/privacy risks;
- context-size/version/dependency risks;
- future-Card leakage;
- blockers to the Exit Gate.

Do not implement during this phase.

## Phase 4 — Define One Bounded Implementation Step

Choose the smallest coherent step that advances the Active Card.

Before writing, state:

```text
Step goal:
Why this step is needed:
Files/areas to inspect or change:
Dependencies/inputs already available:
IBM behavior that must remain unchanged:
Other behavior that must remain unchanged:
Focused validation:
Exit-Gate requirement advanced:
```

Then satisfy the `ROADMAP_ALIGNMENT_GATE` in `AGENTS.md`.

## Phase 5 — Implement

Implement only the approved bounded step.

Follow the Card's architecture, design decision, scope, and out-of-scope rules.

Prefer existing owners and boundaries.

Do not introduce speculative abstractions, unnecessary agents, provider rewrites, UI rewrites, cloud infrastructure, or future V2 behavior unless the Active Card requires them.

Use deterministic software for deterministic responsibilities and LLM reasoning only where it adds value.

## Phase 6 — Validate

Start with the narrowest relevant validation.

Depending on the boundary, verify:
- happy path;
- negative/boundary cases;
- malformed files/model output;
- zero retrieval results;
- retriever/embedding/model/provider failures;
- state/schema invariants;
- relevance/routing;
- retry/termination limits;
- citation/source mapping;
- multi-document behavior;
- cache/session behavior;
- evaluation fixtures.

Use deterministic fakes/stubs for ordinary model unit tests when possible.

If validation fails, diagnose before fixing and do not broaden scope silently.

Run broader relevant tests when a changed contract may affect downstream behavior.

## Phase 7 — Record Evidence

After a meaningful validated step, update the project's approved evidence record.

Record verified facts only:

```text
Implementation:
  exact file / symbol
  what it proves

Tests / Evaluation:
  exact file / case
  actual result

Architecture / Decision:
  exact location when relevant

Prompt / Schema / Configuration:
  exact location when relevant

Runtime / Trace:
  exact location when relevant

Commit:
  hash/message after it exists

Exit Gate:
  requirement advanced

Baseline preservation:
  preserved IBM behavior verified

Remaining:
  work still required
```

Never fabricate evidence.

## Phase 8 — Continue the Same Card

Repeat:

```text
small bounded step
→ implementation
→ focused validation
→ evidence
```

until the complete Exit Gate is satisfied.

Do not switch to a later Card because it is convenient.

Record future capabilities as deferred instead of implementing them early.

## Phase 9 — Complete the Learning Record

Record lessons demonstrated by actual implementation, such as:
- assumptions that proved wrong;
- architectural boundaries that mattered;
- retrieval/agent failure modes;
- why deterministic vs agentic ownership was chosen;
- why a schema/routing/provider decision mattered;
- reusable RAG/agentic-AI engineering lessons.

Do not invent textbook lessons that were not demonstrated.

## Phase 10 — Close the Card

Re-read the exact Exit Gate.

For every requirement, identify concrete proof.

Then:
1. run final required validation/evaluation;
2. inspect final diff/state;
3. reconcile implementation with Card scope and IBM baseline;
4. finalize learning evidence;
5. ensure detailed evidence is current;
6. record commits and intentional deferrals;
7. mark `CLOSED / PASS` only when the entire Exit Gate is proven;
8. stop for human review before beginning the next Card.

If proof is incomplete, keep the Card `IN PROGRESS` or `BLOCKED`.

## Educational Principle

Every Card should improve two things:

1. **Engineering state:** one real, tested capability or reliability improvement.
2. **Learning state:** a future reader can understand what was built, why the boundary exists, how it was validated, and what the implementation demonstrated.

## Non-Goals

This skill does not:
- invent or renumber Cards;
- redesign the roadmap by itself;
- authorize future-Card work;
- replace tests with documentation;
- remove IBM baseline capabilities for convenience;
- treat every component as an agent;
- authorize unrestricted autonomous research;
- create unnecessary provider/cloud abstractions before they are in scope.

## Guiding Flow

**Resolve Card → reconcile repository → inspect/map → bounded step → alignment gate → implement → validate → evidence → repeat → prove Exit Gate → human review.**


## Phase 11 — Mandatory Card Quality Gate

Before closing the active Card, run the complete Quality Gate.

### Required Checks

1. **Focused validation**
   - Run tests/evaluations for the changed boundary.

2. **Relevant regression validation**
   - Run all existing tests relevant to affected behavior.
   - Re-run important checks from previously completed Cards when their contracts could be affected.

3. **Card-specific acceptance/evaluation**
   - Run the exact evaluation required by the Card contract.

4. **Exit Gate proof**
   - Re-read the exact Exit Gate.
   - Map every clause to actual evidence.

5. **Repository review**
   - Run/inspect:
     - `git status`
     - `git diff`
     - changed files
   - Check for unrelated edits, debug code, caches, generated files, secrets, or accidental deletions.

6. **Evidence update**
   - Update `03_CARD_EVIDENCE_MAP.md` with verified implementation, validation, learning, and Exit Gate proof.

7. **Failure behavior**
   - If any required test/evaluation/gate fails:
     - stop;
     - diagnose;
     - keep Card `IN PROGRESS` or `BLOCKED`;
     - do not activate the next Card.

### Required Quality Gate Report

```text
CARD_QUALITY_GATE: PASS | BLOCKED

Card:
Focused tests:
Relevant regression tests:
Card evaluation / acceptance:
Exit Gate proof:
Evidence updated:
git diff reviewed:
git status reviewed:
Unrelated changes:
Secrets / generated artifacts check:
Remaining issues:
Recommended status:
```

The next Card may not start until this gate is `PASS` and the user approves the transition.

## Phase 12 — Write Professional Learning Evidence

For every completed Card, add a concise learning section to `03_CARD_EVIDENCE_MAP.md`.

Use this structure:

```text
Learning Record

What we built:
Why we built it:
Engineering problem:
Agentic AI / RAG concept:
How it works:
Architecture before:
Architecture after:
Important files and ownership:
Tests / evaluations and actual results:
Problem(s) discovered:
How we diagnosed / solved them:
Professional engineering lesson:
Student takeaway:
Exit Gate proof:
What this enables next:
```

Rules:
- Write for an AI/Agentic AI student who should be able to learn from the repository.
- Use simple language for the explanation, but preserve professional terminology.
- Tie every learning claim to actual implementation or validation evidence.
- Do not invent lessons or describe features that are not implemented.
- Explain why a component is an agent, tool, node, deterministic component, or retrieval component when that distinction matters.

## Phase 13 — Git / GitHub Delivery

Git/GitHub delivery happens only after a meaningful step is validated.

### Branch
- Work on the Card branch, not `main`.
- Prefer one branch per Card.

### Commit
- Commit one coherent, validated step.
- Use a clear message describing the real change.
- Do not commit secrets, `.env`, caches, local model weights, or unrelated files.

### Push
- Push stable checkpoints.
- Do not represent broken/incomplete work as complete.

### Pull Request
For a Card PR include:
- Card ID / title;
- goal;
- summary;
- architecture impact;
- validation actually run;
- evidence location;
- limitations / deferred work.

Keep the PR as Draft until the Card Quality Gate passes.

### Merge
Do not merge automatically.

Merge only after:
- Card Quality Gate = PASS;
- evidence updated;
- diff reviewed;
- user approves closure.

Prefer squash merge unless repository policy says otherwise.

After merge, verify repository state before activating the next Card.

## Updated Guiding Flow

**Resolve Card → reconcile repository → inspect/map → bounded step → alignment gate → implement → validate → evidence → commit/push checkpoint → repeat → full regression + Card Quality Gate → learning record → PR review → human approval → merge → next Card.**
