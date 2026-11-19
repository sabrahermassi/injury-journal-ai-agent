from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ask_notes.ingest import IngestResult, ingest_note
from app.core.env import require_env

# Project 2 endpoints. app/api.py plugs this router into the one FastAPI app.
router = APIRouter(tags=["ask notes"])


class NoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000, pattern=r"\S")  # at least one non-space character


@router.post("/notes")
def save_note_endpoint(request: NoteRequest) -> IngestResult:
    """Save a note: extract its fields, chunk it, embed the chunks. Saving it again changes nothing."""
    return ingest_note(request.text, require_env("EMBED_MODEL"))
