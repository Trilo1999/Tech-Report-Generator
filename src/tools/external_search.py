"""
External sources search tool backed by a controlled registry of analyst publications.

Searches research_sources.json, performs keyword/semantic token matching, computes
relevance-weighted reliability scores, and returns standardized [EXT-xx] source records.
"""

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config import RESEARCH_SOURCES_JSON

# Stopwords for lightweight keyword relevance matching
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
    "vs",
    "versus",
    "or",
    "what",
    "how",
    "do",
    "does",
}


def _tokenize(text: str) -> Set[str]:
    """Extract lowercase alphanumeric tokens excluding stopwords."""
    words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def search_external_sources(
    query: str,
    sources_path: Optional[Path] = None,
    min_reliability: float = 0.5,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """
    Search external analyst articles, benchmark publications, and compliance whitepapers.

    Args:
        query: Research query string.
        sources_path: Path to research_sources.json (default: config constant).
        min_reliability: Minimum reliability score filter (default: 0.5).
        limit: Maximum number of sources to return.

    Returns:
        List of formatted external source dictionaries tagged with [EXT-xx].
    """
    if not query or not query.strip():
        return []

    path = sources_path or RESEARCH_SOURCES_JSON
    if not Path(path).is_file():
        raise FileNotFoundError(f"External research sources registry not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sources = data.get("sources", [])
    query_tokens = _tokenize(query)

    scored_sources = []
    for item in sources:
        reliability = float(item.get("reliability_score", 0.7))
        if reliability < min_reliability:
            continue

        title = item.get("title", "")
        snippet = item.get("snippet", "")
        author = item.get("author", "")
        publication = item.get("publication", "")

        doc_text = f"{title} {snippet} {author} {publication}"
        doc_tokens = _tokenize(doc_text)

        # Compute Jaccard/overlap token relevance
        if query_tokens and doc_tokens:
            overlap = query_tokens.intersection(doc_tokens)
            relevance = len(overlap) / len(query_tokens)
        else:
            relevance = 0.0

        # Also give partial credit for substring matches of entire terms (e.g., 'postgresql', 'mongodb')
        for q_token in query_tokens:
            if q_token in doc_text.lower():
                relevance += 0.15

        # Combined ranking score = relevance * 0.6 + reliability * 0.4
        combined_score = (relevance * 0.6) + (reliability * 0.4)

        if relevance > 0:
            scored_sources.append((combined_score, relevance, reliability, item))

    # Sort descending by combined score
    scored_sources.sort(key=lambda x: x[0], reverse=True)

    results: List[Dict[str, Any]] = []
    for idx, (c_score, rel, rel_score, src) in enumerate(scored_sources[:limit], start=1):
        source_id = src.get("id") or f"EXT-{idx:02d}"
        results.append(
            {
                "source_id": source_id,
                "source_type": "external_mock",
                "title": src.get("title", "Untitled Source"),
                "content": src.get("snippet", ""),
                "url": src.get("url", ""),
                "author": src.get("author", "Unknown"),
                "publication": src.get("publication", "External Analyst"),
                "date": src.get("date", "2024-01-01"),
                "reliability_score": rel_score,
                "relevance_score": round(rel, 4),
                "metadata": {
                    "source_id": source_id,
                    "publication": src.get("publication"),
                    "date": src.get("date"),
                    "url": src.get("url"),
                },
            }
        )

    return results


class ExternalSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="Research query string to search peer-reviewed analyst publications, industry whitepapers, and cloud architecture reviews.",
    )
    min_reliability: float = Field(
        0.5,
        description="Minimum reliability score threshold between 0.0 and 1.0 (default: 0.5).",
    )
    limit: int = Field(
        4,
        description="Maximum number of external sources to return (default: 4).",
    )


@tool("search_external_sources", args_schema=ExternalSearchInput)
def search_external_sources_tool(
    query: str,
    min_reliability: float = 0.5,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """
    Search external analyst articles, benchmark publications, and cloud architecture whitepapers.
    Returns ranked citations tagged with [EXT-xx] identifiers.
    """
    return search_external_sources(query=query, min_reliability=min_reliability, limit=limit)
