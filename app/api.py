from fastapi import FastAPI

from app.ask_notes.router import router as ask_notes_router
from app.semantic_search.router import router as semantic_search_router

# One Python service for every project: each project adds its own router here.
app = FastAPI(title="Injury AI service")
app.include_router(semantic_search_router)
app.include_router(ask_notes_router)
