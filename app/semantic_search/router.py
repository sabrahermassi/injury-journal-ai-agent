from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.core.env import require_env
from app.semantic_search.extraction.extract import extract
from app.semantic_search.extraction.schema import Injury
from app.semantic_search.index import IndexSummary, index_and_save
from app.semantic_search.search import MIN_SCORE, SearchFilters, SearchResult, search
from app.semantic_search.store import load

# Project 1 endpoints. app/api.py plugs this router into the one FastAPI app.
router = APIRouter(tags=["semantic search"])


class ExtractRequest(BaseModel):
    note: str = Field(min_length=1)


class IndexRequest(BaseModel):
    notes: list[str] = Field(min_length=1)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    filters: SearchFilters | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=MIN_SCORE, ge=-1, le=1)


@router.post("/extract")
def extract_endpoint(request: ExtractRequest) -> Injury:
    """One note in, the extracted fields out. Nothing is saved."""
    try:
        return extract(request.note)
    except ValidationError:
        raise HTTPException(status_code=502, detail="The model returned invalid fields twice.")


@router.post("/index")
def index_endpoint(request: IndexRequest) -> IndexSummary:
    """Embed, extract and save new notes. Notes already saved are skipped."""
    return index_and_save(request.notes, require_env("EMBED_MODEL"))


@router.get("/body-parts")
def body_parts_endpoint() -> list[str]:
    """Every body part in the saved notes, for the UI's dropdown."""
    parts = {record.fields.body_part.lower() for record in load() if record.fields.body_part}
    return sorted(parts)


@router.post("/search")
def search_endpoint(request: SearchRequest) -> list[SearchResult]:
    """Hybrid search: filter by fields, then rank by meaning."""
    return search(request.query, load(), require_env("EMBED_MODEL"), request.filters, request.top_k, request.min_score)
