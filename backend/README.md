# Mbiu backend

The Django API that checks contracts, and the corpus pipeline that builds its reference library. Both ship in one container image. Setup, configuration and deployment are in the [root README](../README.md); the API itself is described in [docs/api.md](../docs/api.md).

## Layout

```
config/             settings (all from environment variables), URLs, ASGI app
mbiu/
├── api/            endpoints, request and event models (schemas.py), OpenAPI export
├── documents/      upload checks, PDF text extraction (in a separate process), clause splitting
├── contract_map/   whole-contract check: links between clauses, conflicts and overrides
├── corpus/         corpus models and the in-memory snapshot; synthetic.py is the test and outage fallback
├── retrieval/      matching clauses to reference text (Gemini embeddings plus BM25)
├── evaluation/     the check itself: orchestrator.py runs it, verify.py checks every AI answer
├── llm/            Gemini and OpenAI adapters, prompts/ (versioned prompt files)
├── pipeline/       corpus pipeline: fetch, parse, split, tag, check, embed, publish
├── security/       Turnstile verification, log redaction
├── health.py       /healthz and /readyz
└── observability.py tracing and metrics
tests/              pytest suite; refuses to run against a non-local database
```

## Commands

From the repo root, with the local stack running (`just dev`):

```bash
just test        # pytest
just lint        # ruff check and format
just typecheck   # mypy
just types       # regenerate the frontend's API types after changing api/schemas.py
```

Or from `backend/` directly: `uv run pytest`, `uv run ruff check .`, `uv run mypy .`.

## Before you change…

- **A prompt** (`mbiu/llm/prompts/`): add a new versioned file rather than editing the old one, and run the golden set (`evals/`). Read [decision 0002](../docs/adr/0002-ai-output-is-a-proposal.md).
- **Gemini settings** (`mbiu/llm/gemini.py`): read [decision 0004](../docs/adr/0004-gemini-call-settings.md).
- **The event stream or a model in `api/schemas.py`**: update [docs/api.md](../docs/api.md) and run `just types`.
- **The corpus or `corpus/sources.yaml`**: read [docs/corpus.md](../docs/corpus.md).
