# Injury Semantic Search

Search my injury notes by meaning, not just keywords.

## Architecture

```text
React (TypeScript)       localhost:5173   the UI
        │
        ▼
API layer (TypeScript)   localhost:3000   login, notes, database
        │
        ▼
AI service (Python)      localhost:8000   extract, embed, search   ← this repo
        │
        ▼
Ollama                   localhost:11434  the models
```

```text
React ──► TS API endpoints ──► Python endpoints ──► Ollama
          (public)             (internal)
```

Each box is one service (one running program). They talk to each other over HTTP. This repo is the Python AI service.

## How it works

Every RAG app has two flows: **indexing** (saving data) and **querying** (searching it). The extract step uses **structured outputs**: the LLM returns JSON in a fixed shape, validated with Pydantic.

### Indexing: when you save a note

```text
1. You write a messy note
   "Twisted my knee running, pain 6"
        │
        ▼
2. The LLM extracts the fields (structured outputs)
   { body_part: "knee", severity: 6, cause: "running" }
        │
        ▼
3. The embedding model turns the note into a vector
   [0.12, -0.48, 0.91, ...]
        │
        ▼
4. Save note + fields + vector in notes.json
```

### Querying: when you search

```text
1. You type a search
   "knee pain after running"
        │
        ▼
2. The embedding model turns your search into a vector
        │
        ▼
3. Compare it with every saved vector (cosine score, 0 to 1)
        │
        ▼
4. Show the 5 closest notes with their fields
```

Details: [Structured extraction](docs/extraction.md)

## Status

- [x] Milestone 1: Project skeleton (Python)
- [ ] Milestone 2: Structured extraction (rewriting in Python)
- [ ] Milestone 3: Embed and persist
- [ ] Milestone 4: Cosine similarity with tests
- [ ] Milestone 5: CLI search
- [ ] Milestone 6: Threshold experiment
- [ ] Milestone 7: FastAPI endpoints
- [ ] Milestone 8: React search UI

## Tech stack

| Tool         | Why                                                 |
| ------------ | --------------------------------------------------- |
| Python 3.12+ | The AI service                                      |
| uv           | Virtual environment and packages (like npm)         |
| Pydantic     | Validates the LLM's JSON output (like Zod)          |
| pytest       | Tests                                               |
| mypy         | Checks type hints (like tsc)                        |
| Ollama       | Runs the LLM locally, free                          |
| FastAPI      | HTTP endpoints for the TypeScript API (milestone 7) |

Embedding model: chosen in milestone 3 by benchmarking.

## Model choice

Each model extracted 5 fields from the same 10 labelled test notes (`eval/notes.json`), and the benchmark compared its answers to the expected ones.

| Model          | Correct | Failed | Speed         |
| -------------- | ------- | ------ | ------------- |
| llama3.2       | 78%     | 0      | 1.1s/note     |
| **qwen2.5:3b** | **88%** | **0**  | **1.1s/note** |
| qwen2.5:7b     | 88%     | 0      | 2.3s/note     |

Chose **qwen2.5:3b**: same accuracy as the 7B model, as fast as llama3.2, and smaller.

These results come from the first TypeScript version. They will be rerun after the Python rewrite.

To run the benchmark yourself, pull all 3 models, then run it:

```bash
ollama pull llama3.2
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
uv run --env-file .env python -m app.benchmark
```

## Run locally

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com) running locally.

```bash
git clone https://github.com/sabrahermassi/injury-semantic-search.git
cd injury-semantic-search
uv sync
ollama pull qwen2.5:3b
```

Create a `.env` file in the project root:

```
APP_NAME=injury-semantic-search
OLLAMA_URL=http://localhost:11434
LLM_MODEL=qwen2.5:3b
```

- `OLLAMA_URL`: where Ollama runs (default port 11434).
- `LLM_MODEL`: the model used for extraction.

Run the app (always with `-m`, from the project root):

```bash
uv run --env-file .env python -m app.main
```

## Commands

| Command                                          | What it does       |
| ------------------------------------------------ | ------------------ |
| `uv run --env-file .env python -m app.main`      | Runs the app       |
| `uv run pytest`                                  | Runs the tests     |
| `uv run mypy app tests`                          | Checks types       |
| `uv run --env-file .env python -m app.benchmark` | Runs the benchmark |
