# Postgres and pgvector

|                  |                                                                           |
| ---------------- | ------------------------------------------------------------------------- |
| **Database**     | Postgres 17 with the pgvector extension, in Docker (`docker-compose.yml`) |
| **Driver**       | psycopg 3, with plain SQL                                                 |
| **Tables**       | `notes` and `chunks` (`app/ask_notes/schema.sql`)                         |
| **Why**          | One real database for notes, extracted fields and vectors                 |

## Part 1: The general idea

### What pgvector adds

Postgres is a normal database. **pgvector** is a free add-on (an extension) that adds:

- a column type, `vector(768)`, that holds a list of 768 numbers
- operators that measure how close two vectors are
- an index type, **HNSW**, that makes "find the closest vectors" fast

It's turned on once per database with `CREATE EXTENSION vector;`.

### Distance operators

| Operator | Distance              | Note                                    |
| -------- | --------------------- | --------------------------------------- |
| `<=>`    | **Cosine distance**   | **Ours.** 0 = same direction            |
| `<->`    | Euclidean (L2)        | Straight-line distance                  |
| `<#>`    | Inner product         | For vectors already normalized          |

Cosine **similarity** = 1 − cosine **distance**. So "similarity at least 0.54" means "distance at most 0.46".

### Keys and rules

| Word                    | Plain English                                                     | Example in our tables                          |
| ----------------------- | ----------------------------------------------------------------- | ---------------------------------------------- |
| Primary key             | A unique number for each row, picked by Postgres (`BIGSERIAL`)    | `notes.id`, `chunks.id`                        |
| Foreign key             | A column that points to a row in another table                    | `chunks.note_id` points to `notes.id`          |
| `ON DELETE CASCADE`     | Deleting the row pointed to also deletes the rows pointing to it  | Delete a note, its chunks go too               |
| `UNIQUE`                | This value (or combination) can't appear twice                    | `(user_id, content_hash)`: no duplicate notes  |
| `CHECK`                 | The value must pass a test                                        | `severity BETWEEN 1 AND 10`                    |
| `NOT NULL` / `DEFAULT`  | Must have a value / value used when none is given                 | `created_at DEFAULT now()`                     |

The database enforces these rules, so even buggy code can't save bad data.

### Indexes

An index is a **separate, hidden structure** that Postgres keeps next to a table, on one or more of its columns, so searches don't read every row. It changes nothing in the table itself.

- **Normal indexes** (btree) on `(user_id, body_part)`, `(user_id, note_date)` and `chunks(note_id)`.
- **Column order matters**: `(user_id, body_part)` helps "this user's knee notes", not "everyone's knee notes".
- **Cost**: disk space, and slightly slower saves, because every index is updated on every save.

## Part 2: Our tables

```mermaid
flowchart LR
    N["notes"]
    C["chunks"]

    N -->|1 to many| C
```

- **`notes`**: one row per note: who wrote it (`user_id`), the full text, a fingerprint of the text (`content_hash`), and the extracted fields (injury, body part, severity, cause, date) as columns, so filters are plain SQL.
- **`chunks`**: one row per piece of a note: which note (`note_id`), its order (`position`), where it sits in the note (`start_offset`, `end_offset`, for highlighting citations), its text, its vector (`embedding`, 768 numbers) and the model that made it.
- `user_id` is there from day one, so login (Project 5) needs no migration.

## Part 3: How HNSW search works

```sql
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
```

| Part                | Who decides                                                      |
| ------------------- | ---------------------------------------------------------------- |
| `chunks_embedding_idx` | We named it (table_column_idx)                                |
| `USING hnsw`        | Fixed: the index type from pgvector                              |
| `embedding`         | The column to index                                              |
| `vector_cosine_ops` | Fixed name from pgvector: build the index for cosine distance (`<=>`). The query must use the same operator, or the index is ignored |

### What the index stores

A hidden table with one line per chunk:

| Stored          | Example                        |
| --------------- | ------------------------------ |
| A copy of the vector | [0.9, 0.1, ...]           |
| The row's address in `chunks` | row 1            |
| Its closest neighbours | B, C                    |
| Its layers      | bottom, sometimes also top     |

The top layer has few vectors with long links (a highway); the bottom layer has every vector with short links (local streets).

### When a chunk is saved

```mermaid
flowchart LR
    I["INSERT row"]
    F["Find nearby"]
    L["Link to them"]

    I --> F
    F --> L
```

- Postgres saves the row, then updates the index **inside the same INSERT**. Nobody triggers it by hand.
- The index hops through the network to find the new vector's closest vectors (it does not compare with all of them), then links them as neighbours.

### When a question is asked

```mermaid
flowchart LR
    Q["Question"]
    T["Top layer"]
    B["Bottom layer"]
    K["5 closest"]
    S["Threshold"]

    Q --> T
    T --> B
    B --> K
    K --> S
```

- Python embeds the question and runs `ORDER BY embedding <=> question LIMIT 5`.
- The search starts on the top layer, hops to whichever neighbour is closer to the question, then goes down and repeats on the bottom layer.
- It computes the distance only for the vectors it visits: a few hundred, even with millions stored.
- The threshold is a separate step afterwards, in our code.

### It's approximate

- It can miss a true closest vector, usually 1 to 5% of the time, and the miss is almost as close.
- Settings: `hnsw.ef_search` (default 40, higher = misses less, slower search), `m` (default 16 neighbours), `ef_construction` (default 64).
- With few notes, an exact search is fast anyway. At millions of rows, the index makes search 100 to 1000 times faster.

## Trade-offs

| Choice                          | Instead of                       | Why                                                              |
| ------------------------------- | -------------------------------- | ---------------------------------------------------------------- |
| HNSW index                      | Exact search                     | Fast search; costs a small miss rate, slower saves and disk space |
| pgvector inside Postgres        | A separate vector database       | One system; filters and vector search in one query               |
| psycopg + plain SQL             | An ORM (SQLAlchemy)              | You see and learn the real SQL                                   |
| Extracted fields as columns     | A JSON column                    | Indexed filters and database checks                              |
| `user_id` from day one          | Adding it with login later       | No migration later                                               |

## In our code

| File                          | Job                                                             |
| ----------------------------- | --------------------------------------------------------------- |
| `docker-compose.yml`          | Runs Postgres 17 with pgvector, data kept in a volume           |
| `app/core/db.py`              | `connect()`: opens a connection and registers the vector type   |
| `app/ask_notes/schema.sql`    | The tables, rules and indexes                                   |
| `app/ask_notes/setup_db.py`   | Runs `schema.sql`; safe to run again                            |
| `tests/ask_notes/test_db.py`  | 5 tests on a real database, rolled back after each              |

| Test                                   | Checks                                  |
| -------------------------------------- | --------------------------------------- |
| closest chunks come first              | `<=>` orders by cosine distance         |
| same note cannot be saved twice        | `UNIQUE (user_id, content_hash)`        |
| two users can save the same note       | the uniqueness is per user              |
| deleting a note deletes its chunks     | `ON DELETE CASCADE`                     |
| severity must be between 1 and 10      | `CHECK`                                 |

Look inside the database:

```bash
docker compose exec db psql -U injury -d injury_ai -c "\dt" -c "\d chunks"
```

## Read more

- pgvector: https://github.com/pgvector/pgvector
- psycopg 3, basic usage: https://www.psycopg.org/psycopg3/docs/basic/usage.html
- Postgres constraints: https://www.postgresql.org/docs/current/ddl-constraints.html
- Docker Compose: https://docs.docker.com/compose/gettingstarted/
