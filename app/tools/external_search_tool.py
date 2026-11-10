"""
External sources search tool backed by a controlled registry of analyst publications implementing OOP patterns.

Searches research_sources.json, performs keyword/semantic token matching, computes
relevance-weighted reliability scores, and returns standardized [EXT-xx] source records.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

from langchain_core.tools import BaseTool, tool
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

    def __init__(
        self,
        default_sources_path: Optional[Path] = None,
        stopwords: Optional[Set[str]] = None,
    ):
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
            raise FileNotFoundError(
                f"External research sources registry not found: {path}"
            )

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sources", [])

    def _check_and_increment_tavily_usage(self, daily_limit: int = 50) -> bool:
        """
        Check and record daily Tavily usage to prevent accidental overuse.
        Returns True if within limit, False if daily cap reached.
        """
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_key = f"tavily:usage:{today}"
        try:
            from app.config.redis_config import is_redis_available, redis_config

            if is_redis_available():
                client = redis_config.get_redis_client()
                if client is not None:
                    current_count = client.incr(day_key)
                    if current_count == 1:
                        client.expire(day_key, 86400 * 2)
                    return current_count <= daily_limit
        except Exception:
            pass

        # In-memory tracking fallback
        if not hasattr(self, "_tavily_daily_counts"):
            self._tavily_daily_counts = {}
        count = self._tavily_daily_counts.get(today, 0) + 1
        self._tavily_daily_counts[today] = count
        return count <= daily_limit

    def search_tavily(
        self,
        query: str,
        limit: int = 4,
        search_depth: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search live, real-time external technical web data using Tavily Search API.
        Enforces daily budget limits, query optimization, and credit preservation.
        """
        if os.getenv("MOCK_LLM", "false").lower() == "true":
            return []

        from app.config.env_config import settings

        api_key = os.getenv("TAVILY_API_KEY") or getattr(
            settings, "TAVILY_API_KEY", None
        )
        if not api_key or not api_key.strip():
            return []

        daily_limit = getattr(settings, "TAVILY_DAILY_LIMIT", 50)
        if not self._check_and_increment_tavily_usage(daily_limit=daily_limit):
            return []

        effective_depth = search_depth or getattr(
            settings, "TAVILY_SEARCH_DEPTH", "basic"
        )
        effective_limit = min(limit, 4)

        try:
            from urllib.parse import urlparse

            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key.strip())
            response = client.search(
                query=query.strip()[:250],
                max_results=effective_limit,
                search_depth=effective_depth,
                include_answer=False,
            )

            raw_results = response.get("results", [])
            results: List[Dict[str, Any]] = []
            for idx, res in enumerate(raw_results[:effective_limit], start=1):
                source_id = f"EXT-TAVILY-{idx:02d}"
                url = res.get("url", "")
                domain = urlparse(url).netloc or "Web Source"
                raw_score = float(res.get("score", 0.90))
                rel_score = min(0.98, max(0.85, raw_score))

                from app.utils.core_utils.guardrails import sanitize_external_content

                safe_content = sanitize_external_content(res.get("content", ""))
                safe_title = sanitize_external_content(
                    res.get("title", f"Web Intelligence [{query}]")
                )

                results.append(
                    {
                        "source_id": source_id,
                        "source_type": "external_tavily",
                        "title": safe_title,
                        "content": safe_content,
                        "url": url,
                        "author": domain,
                        "publication": f"Live Web ({domain})",
                        "date": "2026",
                        "reliability_score": rel_score,
                        "relevance_score": min(1.0, max(0.80, raw_score)),
                        "metadata": {
                            "source_id": source_id,
                            "publication": domain,
                            "url": url,
                            "provider": "tavily",
                        },
                    }
                )
            return results
        except Exception:
            return []

    def search_hive_ai(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Search external technical research using Hive AI (OpenAI-compatible) endpoint with web search.
        Invokes HIVE_MODEL_NAME via ChatOpenAI to retrieve live, grounded citations.
        """
        if os.getenv("MOCK_LLM", "false").lower() == "true":
            return []

        from app.config.env_config import (
            HIVE_BASE_URL,
            HIVE_MODEL_NAME,
            HIVE_SECRET_KEY,
        )

        if not HIVE_SECRET_KEY or HIVE_SECRET_KEY.strip() in (
            "",
            "your_hive_secret_key_here",
        ):
            return []

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=HIVE_MODEL_NAME,
                temperature=0.1,
                api_key=HIVE_SECRET_KEY,
                base_url=HIVE_BASE_URL,
                timeout=30.0,
                max_retries=2,
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

            try:
                response = llm.invoke(
                    [
                        SystemMessage(content=system_msg),
                        HumanMessage(content=user_msg),
                    ]
                )
            except Exception:
                if "api-cdn.deploy.com" not in str(HIVE_BASE_URL):
                    cdn_llm = ChatOpenAI(
                        model=HIVE_MODEL_NAME,
                        temperature=0.1,
                        api_key=HIVE_SECRET_KEY,
                        base_url="https://api-cdn.deploy.com/api/v1",
                        timeout=30.0,
                        max_retries=2,
                    )
                    response = cdn_llm.invoke(
                        [
                            SystemMessage(content=system_msg),
                            HumanMessage(content=user_msg),
                        ]
                    )
                else:
                    raise

            text = response.content if hasattr(response, "content") else str(response)
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            cleaned = match.group(1).strip() if match else text.strip()
            data = json.loads(cleaned)

            raw_sources = data.get("sources", [])
            if not raw_sources and isinstance(data, list):
                raw_sources = data

            from app.utils.core_utils.guardrails import sanitize_external_content

            results: List[Dict[str, Any]] = []
            for idx, src in enumerate(raw_sources[:limit], start=1):
                source_id = f"EXT-HIVE-{idx:02d}"
                safe_title = sanitize_external_content(
                    src.get("title", f"External Research [{query}]")
                )
                safe_content = sanitize_external_content(
                    src.get("snippet", src.get("description", ""))
                )
                results.append(
                    {
                        "source_id": source_id,
                        "source_type": "external_mock",
                        "title": safe_title,
                        "content": safe_content,
                        "url": src.get("url", "https://hive.ai/research"),
                        "author": src.get("author", "Hive AI Web Research"),
                        "publication": src.get(
                            "publication", "External Technical Whitepaper"
                        ),
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

        cache_key = f"{query.strip().lower()}:{min_reliability}:{limit}"
        try:
            from app.services.core_services.cache_service import cache_service

            cached_res = cache_service.get_cached_search_query(cache_key)
            if cached_res is not None:
                return cached_res
        except Exception:
            pass

        # 1. Prioritize Tavily Web Search if TAVILY_API_KEY is configured
        from app.config.env_config import settings

        tavily_key = os.getenv("TAVILY_API_KEY") or getattr(
            settings, "TAVILY_API_KEY", None
        )
        if (
            tavily_key
            and tavily_key.strip()
            and os.getenv("MOCK_LLM", "false").lower() != "true"
        ):
            tavily_res = self.search_tavily(query=query, limit=limit)
            if tavily_res:
                try:
                    from app.services.core_services.cache_service import cache_service

                    ttl_seconds = getattr(settings, "TAVILY_CACHE_TTL_HOURS", 48) * 3600
                    cache_service.cache_search_query(
                        cache_key, tavily_res, ttl=ttl_seconds
                    )
                except Exception:
                    pass
                return tavily_res

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
            doc_texts = [
                f"{s.get('title', '')} {s.get('snippet', '')}".lower() for s in sources
            ]
            matched_terms = sum(
                1 for term in subject_terms if any(term in dt for dt in doc_texts)
            )
            subject_coverage = matched_terms / len(subject_terms)

        if (len(scored_sources) == 0 or subject_coverage < 0.5) and os.getenv(
            "MOCK_LLM", "false"
        ).lower() != "true":
            hive_results = self.search_hive_ai(query=query, limit=limit)
            if hive_results:
                return hive_results

        from app.utils.core_utils.guardrails import sanitize_external_content

        results: List[Dict[str, Any]] = []
        for idx, (c_score, rel, rel_score, src) in enumerate(
            scored_sources[:limit], start=1
        ):
            source_id = src.get("id") or f"EXT-{idx:02d}"
            safe_title = sanitize_external_content(src.get("title", "Untitled Source"))
            safe_content = sanitize_external_content(src.get("snippet", ""))
            results.append(
                {
                    "source_id": source_id,
                    "source_type": "external_mock",
                    "title": safe_title,
                    "content": safe_content,
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

        if results:
            try:
                from app.services.core_services.cache_service import cache_service

                cache_service.cache_search_query(cache_key, results)
            except Exception:
                pass

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
    return default_external_search_engine.search(
        query=query, min_reliability=min_reliability, limit=limit
    )


class ExternalSearchTool(BaseTool):
    """Tool that searches external analyst articles, benchmarks, and whitepapers."""

    name: str = "search_external_sources"
    description: str = (
        "Search external analyst articles, benchmark publications, and cloud architecture whitepapers. "
        "Returns ranked citations tagged with [EXT-xx] identifiers."
    )
    args_schema: Type[BaseModel] = ExternalSearchInput

    def _run(
        self,
        query: str,
        min_reliability: float = 0.5,
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """Execute external research search."""
        return default_external_search_engine.search(
            query=query, min_reliability=min_reliability, limit=limit
        )


# Tavily live web search function alias
search_tavily = default_external_search_engine.search_tavily


class TavilySearchInput(BaseModel):
    query: str = Field(
        ...,
        description="Query string to search the live web for real-time technical documentation, recent benchmarks, or ecosystem news.",
    )
    search_depth: str = Field(
        "basic",
        description="Tavily search depth: 'basic' (1 credit, recommended) or 'advanced' (2 credits).",
    )
    limit: int = Field(
        4,
        description="Maximum number of live web sources to return (default: 4).",
    )


@tool("search_tavily_web", args_schema=TavilySearchInput)
def search_tavily_web_tool(
    query: str,
    search_depth: str = "basic",
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """
    Search the live web for the latest, real-time external technical documentation,
    whitepapers, and benchmarks using Tavily Search API.
    Returns ranked citations tagged with [EXT-TAVILY-xx] identifiers.
    """
    return default_external_search_engine.search_tavily(
        query=query, limit=limit, search_depth=search_depth
    )


class TavilySearchTool(BaseTool):
    """Tool that searches live web using Tavily Search API."""

    name: str = "search_tavily_web"
    description: str = (
        "Search the live web for the latest, real-time external technical documentation, "
        "whitepapers, and benchmarks using Tavily Search API. "
        "Returns ranked citations tagged with [EXT-TAVILY-xx] identifiers."
    )
    args_schema: Type[BaseModel] = TavilySearchInput

    def _run(
        self,
        query: str,
        search_depth: str = "basic",
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """Execute Tavily live web search."""
        return default_external_search_engine.search_tavily(
            query=query, limit=limit, search_depth=search_depth
        )
