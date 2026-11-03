"""
Internal document search tool backed by Qdrant vector database implementing OOP patterns.

Executes semantic search with all-MiniLM-L6-v2 cosine distance vectors and supports
strict metadata filtering (e.g., doc_type='pdf' vs doc_type='guideline').
Returns standardized [QDR-xx] source records with scores and source metadata.
"""

from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config.env_config import TOP_K_SEARCH_RESULTS
from app.services.core_services.qdrant_ingestion import get_qdrant_client, search_documents


class InternalDocumentRetriever:
    """Object-oriented retriever for proprietary internal guidelines indexed in Qdrant."""

    def __init__(self, default_limit: int = TOP_K_SEARCH_RESULTS, default_min_score: float = 0.25):
        self.default_limit = default_limit
        self.default_min_score = default_min_score

    def build_filter(self, filters: Optional[Dict[str, Any]] = None) -> Optional[Filter]:
        """Convert a dictionary of metadata constraints into a Qdrant Filter object."""
        if not filters:
            return None
        conditions = [FieldCondition(key=key, match=MatchValue(value=value)) for key, value in filters.items()]
        return Filter(must=conditions) if conditions else None

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search proprietary internal documentation in Qdrant with optional metadata filtering."""
        if not query or not query.strip():
            return []

        effective_limit = limit if limit is not None else self.default_limit
        effective_min_score = min_score if min_score is not None else self.default_min_score

        query_filter = self.build_filter(filters)
        client = get_qdrant_client()
        points = search_documents(query=query.strip(), query_filter=query_filter, limit=effective_limit, client=client)

        results: List[Dict[str, Any]] = []
        for idx, point in enumerate(points, start=1):
            if point.score < effective_min_score:
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


# Default singleton instance
default_internal_retriever = InternalDocumentRetriever()

# Backwards compatibility function
search_internal_documents = default_internal_retriever.search


class InternalSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="Natural language semantic search query for internal guidelines, engineering policies, or architecture documentation.",
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata key-value filters, e.g. {'doc_type': 'guideline'} or {'source_file': 'database_comparison.pdf'}.",
    )
    limit: int = Field(
        TOP_K_SEARCH_RESULTS,
        description=f"Maximum number of relevant chunks to retrieve (default: {TOP_K_SEARCH_RESULTS}).",
    )
    min_score: float = Field(
        0.25,
        description="Minimum cosine similarity score threshold (default: 0.25).",
    )


@tool("search_internal_documents", args_schema=InternalSearchInput)
def search_internal_documents_tool(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = TOP_K_SEARCH_RESULTS,
    min_score: float = 0.25,
) -> List[Dict[str, Any]]:
    """
    Search proprietary internal engineering standards, architectural decision records,
    and multi-tenant infrastructure guidelines indexed in the Qdrant vector database.
    Returns ranked chunks tagged with [QDR-xx] identifiers.
    """
    return default_internal_retriever.search(query=query, filters=filters, limit=limit, min_score=min_score)
