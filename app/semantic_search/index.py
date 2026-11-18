import threading
from pathlib import Path

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.core.embed import embed_documents
from app.core.env import require_env
from app.semantic_search.extraction.extract import extract
from app.semantic_search.store import STORE_PATH, NoteRecord, load, note_id, save

NoteList = TypeAdapter(list[str])
INPUT_PATH = Path("data/semantic_search/raw_notes.json")

# Only one load → index → save can run at a time. Without it, two /index calls
# could load the same store, and the last save would delete the other's new notes.
store_lock = threading.Lock()


class IndexSummary(BaseModel):
    total: int
    added: int
    rebuilt: int


def index_notes(notes: list[str], records: list[NoteRecord], embed_model: str) -> list[NoteRecord]:
    # Never mix vectors from different models: keep only records made with this model.
    kept = [record for record in records if record.embed_model == embed_model]
    stale = [record for record in records if record.embed_model != embed_model]

    # Model changed: re-embed the saved notes and reuse their saved fields (no extraction).
    if stale:
        vectors = embed_documents([record.text for record in stale], embed_model)
        for record, vector in zip(stale, vectors, strict=True):
            kept.append(record.model_copy(update={"vector": vector, "embed_model": embed_model}))

    # Notes not saved yet. Compare by id, so "knee pain" and " knee pain " count once.
    done = {record.id for record in kept}
    new_notes: list[str] = []
    for text in notes:
        current_id = note_id(text)
        if current_id not in done:
            done.add(current_id)
            new_notes.append(text)
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


def index_and_save(notes: list[str], embed_model: str, path: Path = STORE_PATH) -> IndexSummary:
    """Load the store, add the new notes, save. Used by the script and by POST /index."""
    with store_lock:
        before = load(path)
        records = index_notes(notes, before, embed_model)
        save(records, path)
    rebuilt = sum(1 for record in before if record.embed_model != embed_model)
    return IndexSummary(total=len(records), added=len(records) - len(before), rebuilt=rebuilt)


def main() -> None:
    notes = NoteList.validate_json(INPUT_PATH.read_text(encoding="utf-8"))
    summary = index_and_save(notes, require_env("EMBED_MODEL"))
    print(f"{summary.total} notes in the store ({summary.added} new, {summary.rebuilt} re-embedded).")


if __name__ == "__main__":
    main()
