from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.ask_notes.router import router as ask_notes_router
from app.core.model_call import ModelUnavailableError
from app.semantic_search.router import router as semantic_search_router

# One Python service for every project: each project adds its own router here.
app = FastAPI(title="Injury AI service")
app.include_router(semantic_search_router)
app.include_router(ask_notes_router)


@app.exception_handler(ModelUnavailableError)
def model_unavailable(request: Request, error: ModelUnavailableError) -> JSONResponse:
    """Any endpoint: when Ollama is down or too slow, answer 503 with a clear message, not a 500."""
    return JSONResponse(status_code=503, content={"detail": str(error)})
