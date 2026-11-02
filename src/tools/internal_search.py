"""
Internal document search tool backed by Qdrant vector database.

Executes semantic search with all-MiniLM-L6-v2 cosine distance vectors and supports
strict metadata filtering (e.g., doc_type='pdf' vs doc_type='guideline').
Returns standardized [QDR-xx] source records with scores and source metadata.
"""

from typing import Any, Dict, List, Optional
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.config import TOP_K_SEARCH_RESULTS
from src.ingestion.ingest_qdrant import get_qdrant_client, search_documents


def search_internal_documents(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = TOP_K_SEARCH_RESULTS,
    min_score: float = 0.25,
) -> List[Dict[str, Any]]:
    """
    Search proprietary internal documentation in Qdrant with optional metadata filtering.

    Args:
        query: Natural language research query.
        filters: Optional key-value filter dict (e.g., {"doc_type": "guideline"}, {"source_file": "database_comparison.pdf"}).
        limit: Maximum number of chunks to return (default: TOP_K_SEARCH_RESULTS).
        min_score: Minimum cosine similarity threshold (default: 0.25).

    Returns:
        List of formatted source dictionaries tagged with [QDR-xx].
    """
    if not query or not query.strip():
        return []

    # Build Qdrant Filter from dictionary if provided
    query_filter: Optional[Filter] = None
    if filters:
        conditions = []
        for key, value in filters.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        if conditions:
            query_filter = Filter(must=conditions)

    client = get_qdrant_client()
    points = search_documents(query=query.strip(), query_filter=query_filter, limit=limit, client=client)

    results: List[Dict[str, Any]] = []
    for idx, point in enumerate(points, start=1):
        if point.score < min_score:
            continue

        payload = point.payload or {}
        section = payload.get("section", "General")
        source_file = payload.get("source_file", "unknown")
        doc_type = payload.get("doc_type", "internal")
        content = payload.get("content", "")

        results.append(
            {
                "source_id": f"QDR-{idx:02d}",
                "source_type": "internal_qdrant",
                "title": f"{source_file} - {section}",
                "content": content,
                "reliability_score": 1.0,  # Internal verified documentation
                "similarity_score": round(float(point.score), 4),
                "metadata": {
                    "source_file": source_file,
                    "doc_type": doc_type,
                    "section": section,
                    "chunk_index": payload.get("chunk_index", 0),
                    "page": payload.get("page"),
                },
            }
        )

    return results
