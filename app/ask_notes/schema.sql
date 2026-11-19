-- Project 2 tables. Safe to run many times: every statement uses IF NOT EXISTS.

CREATE EXTENSION IF NOT EXISTS vector;

-- One row per note. The extracted fields are columns, so filters are plain SQL.
CREATE TABLE IF NOT EXISTS notes (
    id           BIGSERIAL PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,  -- fingerprint of the text: the same note can't be saved twice
    text         TEXT NOT NULL,
    injury       TEXT,
    body_part    TEXT,
    severity     SMALLINT CHECK (severity BETWEEN 1 AND 10),
    cause        TEXT,
    note_date    DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per chunk of a note: its place in the note, its text and its vector.
CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    note_id      BIGINT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,  -- delete a note, its chunks go too
    position     INTEGER NOT NULL,  -- 0, 1, 2, ... order inside the note
    start_offset INTEGER NOT NULL,  -- where the chunk starts in notes.text (for highlighting citations)
    end_offset   INTEGER NOT NULL,
    text         TEXT NOT NULL,
    embedding    vector(768) NOT NULL,  -- nomic-embed-text gives 768 numbers
    embed_model  TEXT NOT NULL,
    UNIQUE (note_id, position, embed_model)  -- re-ingesting a note can't duplicate its chunks
);

-- Fast "closest vectors" search by cosine distance.
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
-- Fast "all chunks of this note".
CREATE INDEX IF NOT EXISTS chunks_note_id_idx ON chunks (note_id);
