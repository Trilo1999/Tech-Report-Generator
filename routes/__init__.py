"""Routes package aggregating all API sub-routers."""

from fastapi import APIRouter

from routes.auth import router as auth_router
from routes.ingest import router as ingest_router
from routes.research import router as research_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(research_router)
api_router.include_router(ingest_router)

__all__ = ["api_router", "auth_router", "ingest_router", "research_router"]
