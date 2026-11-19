# Injury AI assistant

An AI assistant over personal injury notes, built one project at a time: semantic search (P1),
RAG over long notes (P2), retrieval evals (P3), an agent with tools (P4), production pipeline (P5).

## Critical rules

- I am learning. Explain concepts in plain English. Give full files, not partial edits, and the expected output of each step.
- Don't change the project plan or scope unless I ask.
- Don't add, remove or upgrade dependencies (`uv add`, `npm install <package>`) unless I ask. Installing what the lock files already list (`uv sync`, `npm ci`, or `uv run` doing it automatically) is fine.
- Don't commit or push unless I ask.
- Never open, print, log or commit `.env` or files in `data/`. Running the app with `--env-file .env` is fine: the app reads them, you don't. Notes are health data: log a note's id, never its text.

## Layout

- `app/`: Python AI service (FastAPI, port 8000). `app/core/` is shared; one folder per project (`semantic_search`, `ask_notes`). Later projects may reuse earlier projects' code (Ask Notes imports Project 1's extraction and filters); an earlier project never imports a later one.- `api/src/`: TypeScript API (Express + Zod, port 3000), one folder per project. React only calls `/api/...`.
- `web/src/`: React + Vite (port 5173), one folder per project.
- `tests/`, `eval/`, `data/`, `docs/`: same per-project folder names. Python folders `snake_case`, TS and docs `kebab-case`.

## Commands

- Python: `uv run pytest -q` and `uv run mypy app tests`
- TS API: `cd api && npm test && npm run typecheck`
- React: `cd web && npm run build && npm run lint`
- Run: `uv run --env-file .env fastapi dev app/api.py`, `cd api && npm run dev`, `cd web && npm run dev`

## Required after edits

Run the checks for every part you changed. New functions get tests; tests fake the models (monkeypatch), never call Ollama.

## Code rules

- Validate everything that comes in: Zod in the TS API (requests and Python's answers), Pydantic in Python. LLM output is untrusted.
- SQL uses parameters only, never string-built queries.
- Read files as UTF-8; writes to stores are atomic.
- Docs: one per concept in `docs/<project>/`. Mermaid labels 14 characters or fewer, one line, no `<br/>`.

## Git

- One branch per milestone. Commit messages: `type: summary` (feat, fix, docs, chore, refactor).
