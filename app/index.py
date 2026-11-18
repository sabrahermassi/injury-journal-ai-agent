from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.embedding.embed import embed_documents
from app.env import require_env
from app.extraction.extract import extract
from app.store import NoteRecord, load, note_id, save

INPUT_PATH = Path("data/raw_notes.json")
NoteList = TypeAdapter(list[str])


def index_notes(notes: list[str], records: list[NoteRecord], embed_model: str) -> list[NoteRecord]:
    # Never mix vectors from different models: keep only records made with this model.
    kept = [record for record in records if record.embed_model == embed_model]
    stale = [record for record in records if record.embed_model != embed_model]

    # Model changed: re-embed the saved notes with the new model and reuse their saved fields (no extraction, so no note can be lost). If embedding fails, it raises before anything is saved, so the old store stays as it was.
    if stale:
        vectors = embed_documents([record.text for record in stale], embed_model)
        for record, vector in zip(stale, vectors, strict=True):
            kept.append(record.model_copy(update={"vector": vector, "embed_model": embed_model}))

    done = {record.id for record in kept}

    # Notes not saved yet, one per id (the first text wins for duplicates).
    new_notes: list[str] = []
    for note in notes:
        current_id = note_id(note)
        if current_id not in done:
            new_notes.append(note)
            done.add(current_id)
    if not new_notes:
        return kept

    vectors = embed_documents(new_notes, embed_model)
    for text, vector in zip(new_notes, vectors, strict=True):
        try:
            fields = extract(text)
        except ValidationError:
            print(f"Skipped (extraction failed): note {note_id(text)}")
            continue
        kept.append(NoteRecord(id=note_id(text), text=text, fields=fields, vector=vector, embed_model=embed_model))
    return kept


def main() -> None:
    embed_model = require_env("EMBED_MODEL")
    notes = NoteList.validate_json(INPUT_PATH.read_text(encoding="utf-8"))
    before = load()
    records = index_notes(notes, before, embed_model)
    save(records)
    before_ids = {record.id for record in before}
    added = sum(1 for record in records if record.id not in before_ids)
    rebuilt = sum(1 for record in before if record.embed_model != embed_model)
    print(f"{len(records)} notes in the store ({added} new, {rebuilt} re-embedded).")


if __name__ == "__main__":
    main()
