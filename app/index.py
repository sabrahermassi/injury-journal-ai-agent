import json
from pathlib import Path

from pydantic import ValidationError

from app.embedding.embed import embed_documents
from app.env import require_env
from app.extraction.extract import extract
from app.store import NoteRecord, load, note_id, save

INPUT_PATH = Path("data/raw_notes.json")


def index_notes(notes: list[str], records: list[NoteRecord], embed_model: str) -> list[NoteRecord]:
    # Never mix vectors from different models: keep only records made with this model.
    kept = [record for record in records if record.embed_model == embed_model]
    done = {record.id for record in kept}

    # Notes not embedded yet (dict.fromkeys also removes duplicates).
    new_notes = list(dict.fromkeys(note for note in notes if note_id(note) not in done))
    if not new_notes:
        return kept

    vectors = embed_documents(new_notes, embed_model)
    for text, vector in zip(new_notes, vectors, strict=True):
        try:
            fields = extract(text)
        except ValidationError:
            print(f"Skipped (extraction failed): {text}")
            continue
        kept.append(NoteRecord(id=note_id(text), text=text, fields=fields, vector=vector, embed_model=embed_model))
    return kept


def main() -> None:
    embed_model = require_env("EMBED_MODEL")
    notes: list[str] = json.loads(INPUT_PATH.read_text())
    before = load()
    records = index_notes(notes, before, embed_model)
    save(records)
    print(f"{len(records)} notes in the store ({len(records) - len(before)} new).")


if __name__ == "__main__":
    main()
