"""
External sources search tool backed by a controlled registry of analyst publications implementing OOP patterns.

Searches research_sources.json, performs keyword/semantic token matching, computes
relevance-weighted reliability scores, and returns standardized [EXT-xx] source records.
"""

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config.env_config import RESEARCH_SOURCES_JSON

# Stopwords for lightweight keyword relevance matching
STOPWORDS: Set[str] = {
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


class ExternalSearchEngine:
    """Object-oriented search engine for external analyst sources, whitepapers, and live web research."""

    def __init__(self, default_sources_path: Optional[Path] = None, stopwords: Optional[Set[str]] = None):
        self.default_sources_path = default_sources_path or RESEARCH_SOURCES_JSON
        self.stopwords = stopwords or STOPWORDS

    def tokenize(self, text: str) -> Set[str]:
        """Extract lowercase alphanumeric tokens excluding stopwords."""
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", text.lower())
        return {w for w in words if w not in self.stopwords and len(w) > 1}

    def load_sources(self, sources_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Load external research sources registry."""
        path = sources_path or self.default_sources_path
        if not Path(path).is_file():
            raise FileNotFoundError(f"External research sources registry not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sources", [])

    def search_hive_ai(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Search external technical research using Hive AI (OpenAI-compatible) endpoint with web search.
        Invokes HIVE_MODEL_NAME via ChatOpenAI to retrieve live, grounded citations.
        """
        if os.getenv("MOCK_LLM", "false").lower() == "true":
            return []

        from app.config.env_config import HIVE_BASE_URL, HIVE_MODEL_NAME, HIVE_SECRET_KEY

        if not HIVE_SECRET_KEY or HIVE_SECRET_KEY.strip() in ("", "your_hive_secret_key_here"):
            return []

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=HIVE_MODEL_NAME,
                temperature=0.1,
                api_key=HIVE_SECRET_KEY,
                base_url=HIVE_BASE_URL,
            )

            system_msg = (
                "You are an external research engine and technical analyst. "
                "Perform search and analysis for the given technical query. "
                "Return strictly valid JSON with a 'sources' list. "
                "Each item must have: 'title', 'snippet' (detailed technical summary), 'author', 'publication', 'url', 'reliability_score' (0.85-0.98)."
            )
            user_msg = (
                f'Search authoritative external publications, whitepapers, and industry benchmarks for: "{query}". '
                f"Return up to {limit} sources as JSON."
            )

            response = llm.invoke(
                [
                    SystemMessage(content=system_msg),
                    HumanMessage(content=user_msg),
                ]
            )

            text = response.content if hasattr(response, "content") else str(response)
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            cleaned = match.group(1).strip() if match else text.strip()
            data = json.loads(cleaned)

            raw_sources = data.get("sources", [])
            if not raw_sources and isinstance(data, list):
                raw_sources = data

            results: List[Dict[str, Any]] = []
            for idx, src in enumerate(raw_sources[:limit], start=1):
                source_id = f"EXT-HIVE-{idx:02d}"
                results.append(
                    {
                        "source_id": source_id,
                        "source_type": "external_mock",
                        "title": src.get("title", f"External Research [{query}]"),
                        "content": src.get("snippet", src.get("description", "")),
                        "url": src.get("url", "https://hive.ai/research"),
                        "author": src.get("author", "Hive AI Web Research"),
                        "publication": src.get("publication", "External Technical Whitepaper"),
                        "date": src.get("date", "2025-01-01"),
                        "reliability_score": float(src.get("reliability_score", 0.92)),
                        "relevance_score": 0.98,
                        "metadata": {
                            "source_id": source_id,
                            "publication": src.get("publication"),
                            "date": src.get("date"),
                            "url": src.get("url"),
                            "provider": "hive.ai",
                        },
                    }
                )
            return results
        except Exception:
            return []

    def search(
        self,
        query: str,
        sources_path: Optional[Path] = None,
        min_reliability: float = 0.5,
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """Search external analyst articles, benchmark publications, and compliance whitepapers."""
        if not query or not query.strip():
            return []

        sources = self.load_sources(sources_path)
        query_tokens = self.tokenize(query)

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
            doc_tokens = self.tokenize(doc_text)

            # Compute Jaccard/overlap token relevance
            if query_tokens and doc_tokens:
                overlap = query_tokens.intersection(doc_tokens)
                relevance = len(overlap) / len(query_tokens)
            else:
                relevance = 0.0

            # Substring matching for full technical keywords
            for q_token in query_tokens:
                if q_token in doc_text.lower():
                    relevance += 0.15

            combined_score = (relevance * 0.6) + (reliability * 0.4)
            if relevance > 0:
                scored_sources.append((combined_score, relevance, reliability, item))

        scored_sources.sort(key=lambda x: x[0], reverse=True)

        subject_terms = [
            t
            for t in query_tokens
            if len(t) > 3
            and t
            not in {
                "performance",
                "architecture",
                "evaluation",
                "comparison",
                "benchmark",
                "analysis",
                "system",
                "guidelines",
                "standards",
            }
        ]

        subject_coverage = 1.0
        if subject_terms:
            doc_texts = [f"{s.get('title', '')} {s.get('snippet', '')}".lower() for s in sources]
            matched_terms = sum(1 for term in subject_terms if any(term in dt for dt in doc_texts))
            subject_coverage = matched_terms / len(subject_terms)

        if (len(scored_sources) == 0 or subject_coverage < 0.5) and os.getenv("MOCK_LLM", "false").lower() != "true":
            hive_results = self.search_hive_ai(query=query, limit=limit)
            if hive_results:
                return hive_results

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


# Default singleton instance
default_external_search_engine = ExternalSearchEngine()

# Backwards compatibility function
search_external_sources = default_external_search_engine.search


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
    return default_external_search_engine.search(query=query, min_reliability=min_reliability, limit=limit)
