# Verified V1 Demonstrations and Reproducibility Boundaries

This document separates commands that were actually verified from instructions
that require a developer's own local Ollama models or environment.

## Verified deterministic evidence

On the V1-C11 baseline, run from the repository root using the isolated `venv`:

```bash
venv/bin/python -m unittest discover -s test -v
venv/bin/python -m evaluation.run_retrieval_evaluation
venv/bin/python -m evaluation.run_answer_verification_evaluation
venv/bin/python -m pip check
venv/bin/python -m compileall -q agents app.py config document_processor evaluation product providers retriever test utils
```

The C10 baseline evidence recorded:

- deterministic suite: 59/59 tests passed;
- C06 retrieval runner: BM25, vector, and hybrid each measured Hit Rate@3 `1.00`
  and mean Recall@3 `1.00` on four scoreable controlled cases;
- C07 answer/verification runner: 10/10 controlled workflow cases passed;
- C10 operation-routing tests: 5/5 passed;
- a local Gradio `/config` response on port `7862` exposed Research Operation,
  Compare Sources, and Generate Study Questions controls.

These results prove the deterministic fixtures and UI configuration at the
recorded state. They do not prove that every model or every document produces a
high-quality answer.

## Verified local Ollama evidence

V1-C02 exercised a real local Ollama smoke path without downloading a model:

- Ollama runtime `0.31.2`;
- chat model `qwen3.5:4b`;
- embedding model `qwen3-embedding:0.6b`;
- observed embedding dimension `1024`;
- temporary one-chunk hybrid RAG path returned source evidence and completed a
  research/verification path.

That run used environment overrides. The portable `.env.example` defaults are
`llama3.2` and `nomic-embed-text`, so a new developer must inspect `ollama list`
and configure installed model names before attempting a real query.

## Manual product demo

1. Configure `.env` and start `venv/bin/python app.py`.
2. Upload one of the tracked files under `examples/` or your own supported file.
3. Select **Ask** and enter a document question; confirm answer, verification,
   and Sources & Citations outputs appear together.
4. Select **Summarize** or **Key Points** with no focus; then select **Compare
   Sources** with two uploads and an optional comparison focus.
5. Select **Explain Concept** with a concept; select **Generate Study Questions**
   with an optional focus.
6. For any result, inspect citations and treat a `RETRY_EXHAUSTED`, `FAILURE`, or
   unavailable citation outcome as an explicit non-success—not a verified answer.

This is a manual local-model demonstration plan, not an assertion that a model
was downloaded or that these exact interactive queries were executed in C11.

## Reproduction boundary

C11 verifies dependency health, documented configuration names, deterministic
tests/evaluations, compilation, and local Gradio configuration. It does not
create a fresh operating-system image, download Ollama models, or claim a
clean-room real-model query where the needed models are absent. Any developer
reproducing the real path must provide a running local Ollama service and models
appropriate to the configured names.
