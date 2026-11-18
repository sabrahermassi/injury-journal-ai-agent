# Project 2: Ask my notes

Ask questions about your own long injury notes, and get answers that quote the exact passages.

- Long notes are split into chunks, embedded, and stored in Postgres with pgvector.
- A question finds the best chunks (with the same filters as Project 1).
- The LLM answers only from those chunks and cites them; code checks every quote word for word.
- If the notes don't contain the answer, the app says so.

Shared code it uses from `app/core/`: `env.py`, `llm.py`, `embed.py`, `similarity.py`.

Status: in progress.
