import hashlib
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from app.semantic_search.extraction.schema import Injury

STORE_PATH = Path("data/semantic_search/notes.json")


class NoteRecord(BaseModel):
    id: str
    text: str
    fields: Injury
    vector: list[float]
    embed_model: str


RecordList = TypeAdapter(list[NoteRecord])


def note_id(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()[:12]


def load(path: Path = STORE_PATH) -> list[NoteRecord]:
    if not path.exists():
        return []
    return RecordList.validate_json(path.read_text(encoding="utf-8"))


def save(records: list[NoteRecord], path: Path = STORE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        temp_path.write_bytes(RecordList.dump_json(records, indent=2))
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
