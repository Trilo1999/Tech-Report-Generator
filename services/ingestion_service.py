"""Vector database document ingestion and status service."""

import asyncio
from typing import Any, Dict

from fastapi import HTTPException

from src.server.auth import User


async def trigger_document_ingestion(current_user: User) -> Dict[str, Any]:
    """Trigger document parsing, chunking, and vector indexing into Qdrant."""
    from src.ingestion.ingest_qdrant import (
        QDRANT_COLLECTION_NAME,
        get_qdrant_client,
        ingest_all_documents,
    )

    try:
        total_indexed = await asyncio.to_thread(ingest_all_documents, force_recreate=True)
        client = get_qdrant_client()
        info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
        return {
            "status": "success",
            "message": "Document ingestion and vector indexing completed successfully.",
            "collection_name": QDRANT_COLLECTION_NAME,
            "points_indexed": total_indexed,
            "total_points": info.points_count or total_indexed,
            "triggered_by": current_user.email,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion pipeline failed: {str(exc)}",
        ) from exc


def get_ingestion_status() -> Dict[str, Any]:
    """Inspect the current Qdrant vector database collection status and indexed point count."""
    from src.ingestion.ingest_qdrant import (
        QDRANT_COLLECTION_NAME,
        get_qdrant_client,
    )

    try:
        client = get_qdrant_client()
        info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
        return {
            "collection_name": QDRANT_COLLECTION_NAME,
            "status": str(info.status),
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query Qdrant collection status: {str(exc)}",
        ) from exc
