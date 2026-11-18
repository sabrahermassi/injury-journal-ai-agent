from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.env import require_env
from app.extraction.extract import extract
from app.extraction.schema import Injury
from app.index import IndexSummary, index_and_save
from app.search import SearchFilters, SearchResult, search
from app.store import load

app = FastAPI(title="Injury semantic search")


class ExtractRequest(BaseModel):
    note: str = Field(min_length=1)


class IndexRequest(BaseModel):
    notes: list[str] = Field(min_length=1)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    filters: SearchFilters | None = None
    top_k: int = Field(default=5, ge=1, le=50)


@app.post("/extract")
def extract_endpoint(request: ExtractRequest) -> Injury:
    """One note in, the extracted fields out. Nothing is saved."""
    try:
        return extract(request.note)
    except ValidationError:
        raise HTTPException(status_code=502, detail="The model returned invalid fields twice.")


@app.post("/index")
def index_endpoint(request: IndexRequest) -> IndexSummary:
    """Embed, extract and save new notes. Notes already saved are skipped."""
    return index_and_save(request.notes, require_env("EMBED_MODEL"))


@app.post("/search")
def search_endpoint(request: SearchRequest) -> list[SearchResult]:
    """Hybrid search: filter by fields, then rank by meaning."""
    return search(request.query, load(), require_env("EMBED_MODEL"), request.filters, request.top_k)
