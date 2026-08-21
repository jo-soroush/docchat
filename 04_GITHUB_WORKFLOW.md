# DocChat Git & GitHub Workflow

## Purpose

This file defines the professional Git/GitHub workflow for DocChat Cards.

The objective is safe, reviewable, evidence-backed development — not maximum commit frequency.

## 1. Branch Strategy

Do not implement Cards directly on `main`.

Prefer one branch per Card:

```text
codex/v1-c01-baseline-audit
codex/v1-c02-bounded-loop
codex/v1-c03-structured-contracts
codex/v2-c03-react-research
```

Do not mix unrelated Cards on one branch.

## 2. Development Loop

Use this loop inside a Card:

```text
Inspect
→ bounded implementation step
→ focused validation
→ evidence update
→ meaningful commit
→ push stable checkpoint
→ next bounded step
```

Do not create a commit for every trivial edit.

## 3. Commit Rules

Prefer clear Conventional Commit-style messages:

```text
feat: add bounded verification retry state
fix: preserve out-of-scope terminal routing
test: add retry exhaustion coverage
docs: record V1-C02 learning evidence
refactor: isolate typed verification contract
```

A commit must:
- represent one coherent change;
- be understandable from its message;
- not claim tests passed unless they actually ran;
- avoid secrets and machine-local artifacts.

Never commit:
- `.env`;
- API keys/tokens/passwords;
- local model weights;
- caches;
- temporary debug output;
- unrelated generated artifacts.

## 4. Push Rules

Push after a meaningful validated checkpoint.

Do not push broken work as if it were ready.

An in-progress branch may be pushed for backup/collaboration, but must remain clearly in progress and must not be merged.

## 5. Pull Requests

Create a Draft PR while the Card is in progress.

PR description should include:

```text
Card:
Goal:
Why:
Summary of changes:
Architecture impact:
Tests / evaluations actually executed:
Evidence:
Known limitations:
Deferred work:
Quality Gate:
```

Do not mark the PR ready until `CARD_QUALITY_GATE: PASS`.

## 6. Mandatory Pre-Merge Gate

Before merge:

1. run focused tests;
2. run all relevant existing tests;
3. run Card-specific evaluation/acceptance;
4. confirm prior completed Cards have no relevant regression;
5. prove every Exit Gate clause;
6. update learning/evidence;
7. review `git diff`;
8. review `git status`;
9. check for secrets/unrelated/generated files;
10. obtain human approval.

If any item fails, do not merge.

## 7. Merge Policy

Default:
- Draft PR while active;
- human review before merge;
- no auto-merge;
- prefer **Squash merge** for a clean Card history.

After merge:
- verify target branch state;
- verify expected files/history;
- only then activate the next Card.

## 8. Force Push

Avoid force push by default.

Do not rewrite shared history simply to make the history look cleaner.

## 9. GitHub as Professional Evidence

GitHub should make it possible to reconstruct:

- what changed;
- why;
- under which Card;
- what was tested;
- what evidence proved completion;
- who approved the transition;
- what architectural decisions were made.

GitHub supports project traceability, but the authorities remain:

**Repository reality → Roadmap / Card contract → verified Evidence Map → Git/GitHub history.**

## 10. Card Transition Rule

Codex must never move automatically from Card N to Card N+1.

Required transition:

```text
Card implementation complete
→ full relevant validation
→ regression checks
→ Evidence + Learning Record complete
→ CARD_QUALITY_GATE: PASS
→ PR review
→ human approval
→ merge
→ post-merge verification
→ next Card may begin
```
