# Project 1: Semantic search

Search injury notes by meaning, and filter by the fields an LLM extracted from each note.

| File                                  | Job                                                          |
| ------------------------------------- | ------------------------------------------------------------ |
| `extraction/schema.py`, `extract.py`  | The LLM turns a messy note into validated fields (`Injury`)   |
| `store.py`                            | `NoteRecord`, and atomic `load` / `save` of the notes store   |
| `index.py`                            | Skip saved notes, embed new ones, extract their fields, save  |
| `search.py`                           | Hybrid search: filter by fields, rank by cosine, threshold    |
| `router.py`                           | `/extract`, `/index`, `/body-parts`, `/search`                |
| `evaluation/`                         | Extraction benchmark, embedding benchmark, threshold experiment |

Shared code it uses from `app/core/`: `env.py`, `llm.py`, `embed.py`, `similarity.py`.

- Docs: [`docs/semantic-search/`](../../docs/semantic-search/)
- Tests: [`tests/semantic_search/`](../../tests/semantic_search/)
- Finished version: tag [`p1-semantic-search`](https://github.com/sabrahermassi/injury-semantic-search/tree/p1-semantic-search)
