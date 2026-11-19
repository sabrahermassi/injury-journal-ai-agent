from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.ask_notes.ingest import IngestResult, ingest_note
from app.ask_notes.retrieve import RetrievedChunk, retrieve
from app.core.env import require_env
from app.semantic_search.search import SearchFilters

# Project 2 endpoints. app/api.py plugs this router into the one FastAPI app.
router = APIRouter(tags=["ask notes"])


class NoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000, pattern=r"\S")  # at least one non-space character

    @field_validator("text")
    @classmethod
    def no_nul_character(cls, text: str) -> str:
        # Postgres text columns can't store the NUL character: reject it here with a 422, not a 500 later.
        if "\x00" in text:
            raise ValueError("text must not contain the NUL character")
        return text


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000, pattern=r"\S")
    filters: SearchFilters | None = None
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/notes")
def save_note_endpoint(request: NoteRequest) -> IngestResult:
    """Save a note: extract its fields, chunk it, embed the chunks. Saving it again changes nothing."""
    return ingest_note(request.text, require_env("EMBED_MODEL"))


@router.post("/retrieve")
def retrieve_endpoint(request: RetrieveRequest) -> list[RetrievedChunk]:
    """Question in, the closest chunks out (best first), filtered by body part, severity and dates."""
    return retrieve(request.question, require_env("EMBED_MODEL"), request.filters, request.top_k)
