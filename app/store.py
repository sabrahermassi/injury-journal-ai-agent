import hashlib
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from app.extraction.schema import Injury

STORE_PATH = Path("data/notes.json")


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
    return RecordList.validate_json(path.read_text())


def save(records: list[NoteRecord], path: Path = STORE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(RecordList.dump_json(records, indent=2))
