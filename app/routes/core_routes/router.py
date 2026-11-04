from fastapi import APIRouter

from app.routes.core_routes.auth_route import router as auth_router
from app.routes.core_routes.cache_route import router as cache_router
from app.routes.core_routes.chat_route import router as chat_router
from app.routes.core_routes.ingest_route import router as ingest_router
from app.routes.core_routes.ingestion_route import router as ingestion_router
from app.routes.core_routes.research_route import router as research_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(cache_router)
router.include_router(ingestion_router)
router.include_router(auth_router)
router.include_router(ingest_router)
router.include_router(research_router)
