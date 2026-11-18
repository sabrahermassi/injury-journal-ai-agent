# Embedding model

|                    |                                                                                  |
| ------------------ | -------------------------------------------------------------------------------- |
| **Model**          | `nomic-embed-text` (via Ollama), to be confirmed by the benchmark in milestone 4 |
| **Type**           | Embedding model (not generative: it never writes text)                           |
| **What it does**   | Text in, vector out (a list of numbers)                                          |
| **Why we need it** | Lets the app find notes **by meaning**, not by exact words (semantic search)     |

## Part 1: How embedding models work (the general idea)

### What a vector is

An embedding model turns text into a **list of numbers**, called a vector. `nomic-embed-text` gives 768 numbers per text.

```text
"knee pain after running"  ──► embedding model ──►  [0.012, -0.044, 0.091, ... 768 numbers]
```

You can't read the numbers, but they encode **meaning**. Texts with similar meaning get vectors that point in a similar direction.

```text
"hurt my shin jogging"       ●  ●  "knee pain after running"     ← close: similar meaning


"cut my finger chopping onions"        ●                          ← far: different meaning
```

That's why "running injury" can find "hurt my shin jogging" even though the two share no words.

### LLM vs embedding model

|          | LLM (`qwen2.5:3b`) | Embedding model (`nomic-embed-text`) |
| -------- | ------------------ | ------------------------------------ |
| Output   | Text               | Numbers (a vector)                   |
| Size     | ~1.9 GB            | ~274 MB                              |
| Speed    | ~1 s per note      | Milliseconds per note                |
| Used for | Extraction         | Search by meaning                    |

### The rules

1. **Use the same model for notes and for search questions.** Vectors from different models are not comparable.
2. **Never mix models in one store.** Changing the model means re-embedding every note.
3. **Some models need a prefix.** `nomic-embed-text` expects `search_document: ` before notes and `search_query: ` before questions. Without it, results get worse with no error.
4. **You can't turn a vector back into text.** Always keep the original note.

### Settings we use

```python
client.embed(
    model="nomic-embed-text",                       # which embedding model
    input=["search_document: knee pain 5/10", "search_document: sore neck"],  # one or more texts, with the prefix
)
# response.embeddings → one vector per text, in the same order
```

Compared with `client.chat`:

| `client.chat` (LLM)                       | `client.embed` (embedding model)                                     |
| ----------------------------------------- | -------------------------------------------------------------------- |
| `messages`: a conversation with roles     | `input`: just a list of texts, no roles                              |
| `format="json"`, `temperature=0`          | No format or temperature: the same text always gives the same vector |
| Returns text (`response.message.content`) | Returns vectors (`response.embeddings`)                              |
| One conversation per call                 | Many texts per call (batching), which is faster                      |

## Part 2: How our embedding works

### Saving notes (indexing)

The same note goes to both models, side by side:

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
               Save note + fields + vector in data/notes.json
```

First create `data/raw_notes.json`: a UTF-8 JSON array of strings, one note each. `data/` is in `.gitignore`, so it isn't in the repo.

```json
["knee pain after running", "lower back hurts after sitting all day"]
```

Then run:

```bash
uv run --env-file .env python -m app.index
```

```text
data/raw_notes.json
        │
        ▼
Skip notes already saved with this model   ← note_id = fingerprint of the text
        │
        ▼
embed_documents(new notes)                 ← all at once, with "search_document: "
        │
        ▼
extract(each note)                         ← fields, one note at a time
        │
        ▼
data/notes.json   { id, text, fields, vector, embed_model }
```

### The files

| File                     | Job                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------- |
| `app/embedding/embed.py` | `embed_documents` (notes) and `embed_query` (search questions), with the right prefix |
| `app/store.py`           | `NoteRecord`, plus `load` and `save` for `data/notes.json`                            |
| `app/index.py`           | The pipeline: skip, embed, extract, save                                              |

### Searching (coming in milestones 4 and 5)

```text
"knee pain after running"
        │
        ▼
embed_query  ──► vector (not saved)        ← with "search_query: "
        │
        ▼
Cosine similarity vs every saved vector    ← milestone 4
        │
        ▼
Top 5 closest notes                        ← milestone 5
```

## Cosine similarity

_To be added in milestone 4._
