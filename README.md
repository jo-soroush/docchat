# DocChat

DocChat is a local-first, source-grounded personal research assistant for uploaded
PDF, DOCX, TXT, and Markdown documents. V1 preserves useful IBM Skills Network
DocChat capabilities and provenance while running independently through a
vendor-neutral provider boundary with Ollama as the first local implementation.

## What V1 provides

- Docling-based document conversion, Markdown-aware chunking, hashing, caching,
  and duplicate-chunk removal.
- Chroma vector retrieval plus BM25 keyword retrieval combined as hybrid RAG.
- Typed relevance, research, and verification contracts in a bounded LangGraph
  workflow.
- Stable document/chunk provenance and user-visible sources and citations.
- Safe per-run traces and explicit, non-fabricating failure outcomes.
- Gradio study operations: Ask, Summarize, Key Points, Compare Sources, Explain
  Concept, and Generate Study Questions.
- Deterministic retrieval, answer/verification, workflow, citation, trace, and
  failure regression suites.

## Quick start

This V1 path was verified on macOS with Python 3.11.15. It uses an isolated
repository virtual environment and does not require an IBM account, IBM project,
or API key.

```bash
git clone <your-fork-or-clone-url>
cd docchat
python3.11 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Install and run [Ollama](https://ollama.com/) locally, then inspect the models
available on your machine:

```bash
ollama --version
ollama list
```

The `.env.example` defaults expect `llama3.2` for chat and `nomic-embed-text`
for embeddings at `http://127.0.0.1:11434`. Configure `OLLAMA_CHAT_MODEL` and
`OLLAMA_EMBEDDING_MODEL` in your untracked `.env` to model names already
available locally. If the default models are absent, obtain them through Ollama
according to your own download policy; model weights are never committed here.

Start the application:

```bash
venv/bin/python app.py
```

Open the local URL shown by Gradio (default `http://127.0.0.1:7860`). If that
port is in use, set `GRADIO_SERVER_PORT` in `.env` to another local port. The
application binds to `127.0.0.1`.

## Configure locally

Copy `.env.example` to `.env`; never commit `.env`. The active configuration
boundary is `config/settings.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama service URL. |
| `OLLAMA_CHAT_MODEL` | `llama3.2` | Chat model used by relevance, research, and verification. |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model used by vector retrieval. |
| `GRADIO_SERVER_PORT` | `7860` | Local Gradio port; validated from 1–65535. |
| `MAX_VERIFICATION_RETRIES` | `2` | Allowed re-research attempts after failed verification; validated from 0–5. |
| `CHROMA_DB_PATH` | `./chroma_db` | Local persistent vector-store directory. |
| `CHROMA_COLLECTION_NAME` | `documents` | Explicit vector collection for stable, active-upload-scoped records. |

These values are configuration, not credentials. There is no active IBM,
Watsonx, or OpenAI runtime configuration in V1.

## Use DocChat

1. Upload one or more `.pdf`, `.docx`, `.txt`, or `.md` files.
2. Select a **Research Operation**:
   - **Ask**: enter a document question.
   - **Summarize**, **Key Points**, **Compare Sources**, or **Generate Study
     Questions**: optionally provide a focus.
   - **Explain Concept**: provide the concept to explain.
3. Run the operation. The product adapter converts the selection into an ordinary
   question and delegates to the same verified backend workflow.
4. Read the answer, verification report, and **Sources & Citations** together.

The session retriever is reused while the uploaded file hash set is unchanged.
Changing uploads rebuilds the document/retrieval path.

## Architecture at a glance

```text
Gradio product adapter
  → document validation / Docling / Markdown chunks / cache / provenance
  → BM25 + Chroma vector search → hybrid retriever
  → typed relevance → typed research → typed verification
  → bounded correction route → terminal outcome
  → answer + verification report + citations + safe run trace

DocChat Core → ChatProvider / EmbeddingProvider → Ollama local runtime
```

See [architecture documentation](docs/ARCHITECTURE.md) for ownership, contracts,
data flow, and failure behavior. See [provenance and decisions](docs/PROVENANCE_AND_DECISIONS.md)
for the historical IBM baseline and V1 extensions.

## Reproduce V1 checks

Run these from the repository root after installing dependencies. The deterministic
suite uses fakes where appropriate and does not require a model download.

```bash
venv/bin/python -m unittest discover -s test -v
venv/bin/python -m evaluation.run_retrieval_evaluation
venv/bin/python -m evaluation.run_answer_verification_evaluation
venv/bin/python -m pip check
venv/bin/python -m compileall -q agents app.py config document_processor evaluation product providers retriever test utils
```

The retrieval runner measures BM25, vector, and hybrid retrieval at a common
K=3. The answer/verification runner measures retrieval preconditions, answer
behavior, citation grounding, typed verification, and routing separately. See
[verified demos and results](docs/VERIFIED_DEMOS.md) for actual V1 evidence and
the boundaries of what was tested.

## Limitations and V2 boundary

V1 is a local single-user research assistant, not a production deployment. Its
small deterministic fixtures do not prove broad real-model quality; no cloud
provider, multi-provider failover, persistent research library, telemetry
backend, authentication, or multi-user isolation is implemented. A model must
also follow the required structured JSON contracts for real workflow calls.

V2 begins only after V1 closure and will add explicitly approved source routing,
tooling, security, persistent collections, and deployment boundaries. It does
not exist in the active V1 runtime.

## Provenance

IBM Skills Network DocChat history is preserved as provenance. The selected
historical baseline is IBM remote `origin/2-final` commit `eb9be30`; V1 removes
its active IBM runtime dependency but does not erase that history. No `LICENSE*`
file was present in the audited baseline or active repository, so do not infer a
license from this documentation. See the provenance record before redistributing
or relicensing the project.
