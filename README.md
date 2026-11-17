# Injury Semantic Search

Search my injury notes by meaning, not just keywords.

## How it works

Every RAG app has two flows: **indexing** (saving data) and **querying** (searching it). The extract step uses **structured outputs**: the LLM returns JSON in a fixed shape, validated with Zod.

### Indexing: when you save a note

```mermaid
flowchart TD
    A["1. You write a messy note<br/>'Twisted my knee running, pain 6'"]
    B["2. The LLM extracts the fields<br/>(structured outputs)<br/>bodyPart: knee, severity: 6, cause: running"]
    C["3. The embedding model turns<br/>the note into a vector<br/>[0.12, -0.48, 0.91, ...]"]
    D["4. Save note + fields + vector<br/>in notes.json"]
    A --> B --> C --> D
```

### Querying: when you search

```mermaid
flowchart TD
    A["1. You type a search<br/>'knee pain after running'"]
    B["2. The embedding model turns<br/>your search into a vector"]
    C["3. Compare it with every saved vector<br/>(cosine score, 0 to 1)"]
    D["4. Show the 5 closest notes<br/>with their fields"]
    A --> B --> C --> D
```

Details: [Structured extraction](docs/extraction.md)

## Status

- [x] Milestone 1: Project skeleton
- [ ] Milestone 2: Structured extraction (choose models)
- [ ] Milestone 3: Embed and persist
- [ ] Milestone 4: Cosine similarity with tests
- [ ] Milestone 5: CLI search
- [ ] Milestone 6: Threshold experiment
- [ ] Milestone 7: React search UI

## Tech stack

| Tool                | Why                                         |
| ------------------- | ------------------------------------------- |
| Node.js 20+         | Runtime; built-in `--env-file` loads `.env` |
| TypeScript (strict) | Type safety                                 |
| tsx                 | Runs `.ts` files directly, no build step    |
| Vitest              | Tests                                       |
| npm                 | Package manager                             |

LLM and embedding models: chosen in milestone 2 by benchmarking (local Ollama, free).

## Run locally

Requires Node.js 20+.

```bash
git clone https://github.com/sabrahermassi/injury-semantic-search.git
cd injury-semantic-search
npm install
```

Create a `.env` file in the project root:

```
APP_NAME=injury-semantic-search
```

## Scripts

| Command             | What it does   |
| ------------------- | -------------- |
| `npm start`         | Runs the app   |
| `npm test`          | Runs the tests |
| `npm run typecheck` | Checks types   |
