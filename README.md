# Injury Semantic Search

Search my injury notes by meaning, not just keywords.

## Architecture

```text
          You write a messy note: "Twisted my knee running, pain 6"
                     │                              │
                     ▼                              ▼
       LLM extracts the fields          Embedding model turns the
       (structured outputs)             note text into a vector
       { body_part: "knee",             [0.12, -0.48, 0.91, ...]
         severity: 6,                   for search by meaning
         cause: "running" }
       for showing, filtering, charts
                     │                              │
                     └──────────────┬───────────────┘
                                    ▼
               Save note + fields + vector in notes.json
```

The same note goes to **both** models, side by side:

- **Fields** (`{ body_part: "knee", severity: 6 }`) are for showing, filtering and charts.
- **Vector** (`[0.12, -0.48, ...]`) is for search by meaning.

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

## Learn more

- [Structured extraction](docs/structured-extraction.md): the LLM, how `messages` and roles work, and how a messy note becomes validated fields.
- [Embedding model](docs/embedding-model.md): what vectors are, the rules for using them, and how notes are embedded and saved.

## Status

- [x] Milestone 1: Project skeleton (Python)
- [x] Milestone 2: Structured extraction (Python)
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

Each model extracted 5 fields from the same 10 labelled test notes (`eval/notes.json`), and `app/benchmark.py` compared its answers to the expected ones.

| Model          | Correct | Failed | Speed         |
| -------------- | ------- | ------ | ------------- |
| llama3.2       | 78%     | 0      | 1.2s/note     |
| **qwen2.5:3b** | **86%** | **0**  | **1.2s/note** |
| qwen2.5:7b     | 88%     | 0      | 2.4s/note     |

Chose **qwen2.5:3b**: only 1 field fewer than the 7B model (43 vs 44 out of 50), twice as fast, and smaller.

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
ollama pull nomic-embed-text
```

Create a `.env` file in the project root:

```
APP_NAME=injury-semantic-search
OLLAMA_URL=http://localhost:11434
LLM_MODEL=qwen2.5:3b
EMBED_MODEL=nomic-embed-text
```

- `OLLAMA_URL`: where Ollama runs (default port 11434).
- `LLM_MODEL`: the model used for extraction.
- `EMBED_MODEL`: the model used for embeddings.

Run the app (always with `-m`, from the project root):

```bash
uv run --env-file .env python -m app.main
```

### Index your notes

Create `data/raw_notes.json`: a UTF-8 JSON array of strings, one note each. `data/` is in `.gitignore`, so personal health notes are never committed.

```json
["knee pain after running", "lower back hurts after sitting all day"]
```

Then run:

```bash
uv run --env-file .env python -m app.index
```

Each note is extracted and embedded, then saved in `data/notes.json`.

## Commands

| Command                                          | What it does       |
| ------------------------------------------------ | ------------------ |
| `uv run --env-file .env python -m app.main`      | Runs the app       |
| `uv run pytest`                                  | Runs the tests     |
| `uv run mypy app tests`                          | Checks types       |
| `uv run --env-file .env python -m app.benchmark` | Runs the benchmark |
