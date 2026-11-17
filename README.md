# Injury Semantic Search

Search my injury notes by meaning, not just keywords.

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
