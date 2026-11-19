import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import iterate_in_threadpool

from app.ask_notes.answer import AskResult, ask
from app.ask_notes.ingest import IngestResult, Note, get_note, ingest_note
from app.ask_notes.retrieve import RetrievedChunk, retrieve
from app.ask_notes.stream import ask_stream
from app.core.model_call import ModelUnavailableError
from app.core.env import require_env
from app.semantic_search.search import SearchFilters

logger = logging.getLogger(__name__)

# Project 2 endpoints. app/api.py plugs this router into the one FastAPI app.
router = APIRouter(tags=["ask notes"])


def reject_nul(text: str) -> str:
    """Postgres text can't store the NUL character: reject it with a 422 here, not a 500 later."""
    if "\x00" in text:
        raise ValueError("must not contain the NUL character")
    return text


class NoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000, pattern=r"\S")  # at least one non-space character

    @field_validator("text")
    @classmethod
    def no_nul_character(cls, text: str) -> str:
        return reject_nul(text)


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000, pattern=r"\S")
    filters: SearchFilters | None = None
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def no_nul_in_question(cls, question: str) -> str:
        return reject_nul(question)

    @field_validator("filters")
    @classmethod
    def no_nul_in_body_part(cls, filters: SearchFilters | None) -> SearchFilters | None:
        if filters is not None and filters.body_part is not None:
            reject_nul(filters.body_part)
        return filters


@router.post("/notes")
def save_note_endpoint(request: NoteRequest) -> IngestResult:
    """Save a note: extract its fields, chunk it, embed the chunks. Saving it again changes nothing."""
    return ingest_note(request.text, require_env("EMBED_MODEL"))


@router.post("/retrieve")
def retrieve_endpoint(request: RetrieveRequest) -> list[RetrievedChunk]:
    """Question in, the closest chunks out (best first), filtered by body part, severity and dates."""
    return retrieve(request.question, require_env("EMBED_MODEL"), request.filters, request.top_k)


@router.post("/ask")
def ask_endpoint(request: RetrieveRequest) -> AskResult:
    """Question in, an answer with checked quotes out, or a refusal if no quote can be verified."""
    return ask(request.question, require_env("EMBED_MODEL"), request.filters, request.top_k)


@router.post("/ask/stream")
async def ask_stream_endpoint(request: RetrieveRequest, http: Request) -> StreamingResponse:
    """Like /ask, but sends events (Server-Sent Events) while the answer is being written.

    If the user leaves, the browser closes the connection: we stop reading, which stops the model.
    """
    events = ask_stream(request.question, require_env("EMBED_MODEL"), request.filters, request.top_k)

    async def body() -> AsyncIterator[str]:
        try:
            async for event in iterate_in_threadpool(events):
                if await http.is_disconnected():
                    logger.info("client left, stopped generating")
                    break
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except ModelUnavailableError as error:
            yield f"data: {json.dumps({'type': 'error', 'message': str(error)})}\n\n"
        finally:
            events.close()  # closes the model stream too

    return StreamingResponse(body(), media_type="text/event-stream")


@router.get("/notes/{note_id}")
def get_note_endpoint(note_id: int) -> Note:
    """One full note, so the page can show a citation in context and highlight the quote."""
    note = get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    return note
