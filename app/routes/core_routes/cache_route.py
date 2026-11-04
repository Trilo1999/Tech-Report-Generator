"""Cache diagnostic and management routes."""

from fastapi import APIRouter

from app.schemas.core_schemas.cache_schema import (
    CacheClearRequest,
    CacheClearResponse,
    CacheStatusResponse,
)
from app.services.core_services.cache_service import cache_service

router = APIRouter(prefix="/cache", tags=["Cache Management"])


@router.get("/status", response_model=CacheStatusResponse)
async def get_cache_status():
    """Retrieve operational diagnostics and status of the caching system.

    Returns:
        CacheStatusResponse with active backend ('redis' or 'in_memory'), host, port, db,
        TTL configuration, and stored key count.
    """
    return cache_service.get_status()


@router.post("/clear", response_model=CacheClearResponse)
async def clear_cache(request: CacheClearRequest = CacheClearRequest()):
    """Clear cached entries by optional prefix, or flush all keys if prefix is omitted.

    Args:
        request: CacheClearRequest with optional prefix.

    Returns:
        CacheClearResponse with count of cleared keys.
    """
    prefix = request.prefix or ""
    cleared = cache_service.clear_prefix(prefix)
    status_info = cache_service.get_status()
    return {
        "status": "success",
        "cleared_keys": cleared,
        "prefix": prefix if prefix else None,
        "backend": status_info["backend"],
    }
