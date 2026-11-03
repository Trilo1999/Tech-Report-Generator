"""Vector database ingestion routes."""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.services.core_services.ingestion_service import (
    get_ingestion_status,
    trigger_document_ingestion,
)
from app.services.iam_services.research_auth import (
    User,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/api/research/ingest", tags=["Ingestion"])


@router.post("")
@router.post("/")
async def run_ingestion(
    current_user: User = Depends(require_roles(["admin", "researcher"])),
) -> Dict[str, Any]:
    """Trigger document parsing, chunking, and vector indexing into Qdrant."""
    return await trigger_document_ingestion(current_user)


@router.get("/status")
async def read_ingestion_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Inspect the current Qdrant vector database collection status and indexed point count."""
    return get_ingestion_status()
