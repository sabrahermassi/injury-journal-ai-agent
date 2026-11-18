from fastapi import FastAPI

from app.semantic_search.router import router as semantic_search_router

# One Python service for every project: each project adds its own router here.
app = FastAPI(title="Injury AI service")
app.include_router(semantic_search_router)
