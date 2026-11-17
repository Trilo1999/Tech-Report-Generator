"""
Semantic Response Caching Service powered by Vector Similarity and Redis.

Caches query responses and retrieves them based on semantic vector similarity
rather than exact string matching, dramatically reducing redundant LLM calls and latency.
"""

import json
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from app.config.redis_config import is_redis_available, redis_config

logger = logging.getLogger("research_agent.semantic_cache")


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(v1) != len(v2) or not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class SemanticCacheService:
    """Vector-based semantic response caching service with Redis and in-memory fallback."""

    def __init__(
        self,
        default_threshold: float = 0.90,
        default_ttl: int = 3600,
        redis_prefix: str = "semantic_cache",
    ) -> None:
        self.default_threshold = default_threshold
        self.default_ttl = default_ttl
        self.redis_prefix = redis_prefix
        # In-memory store: {query_hash: (query, vector, response, expires_at, metadata)}
        self._in_memory_store: Dict[
            str, Tuple[str, List[float], Any, float, Dict[str, Any]]
        ] = {}
        self._hits = 0
        self._misses = 0

    def _get_embedding(self, text: str) -> List[float]:
        """Compute embedding vector for a text query."""
        from app.utils.core_utils.embedding_utils import embeddings_client

        return embeddings_client.embed_query(text)

    def _get_redis_client(self):
        """Retrieve Redis client if available."""
        if not is_redis_available():
            return None
        return redis_config.get_redis_client()

    def get(
        self, query: str, threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Look up a query semantically using cosine vector similarity.

        Args:
            query: Input question or search prompt.
            threshold: Minimum cosine similarity threshold (default: 0.90).

        Returns:
            Dict with 'cached_response', 'similarity_score', 'matched_query' if found, else None.
        """
        if not query or not query.strip():
            return None

        sim_threshold = threshold if threshold is not None else self.default_threshold
        query_vector = self._get_embedding(query.strip())
        now = time.time()

        r_client = self._get_redis_client()
        best_match: Optional[Dict[str, Any]] = None
        highest_sim = -1.0

        if r_client is not None:
            try:
                # Scan semantic cache index keys
                index_key = f"{self.redis_prefix}:index"
                entry_keys = r_client.smembers(index_key) or []
                for raw_key in entry_keys:
                    k = (
                        raw_key.decode("utf-8")
                        if isinstance(raw_key, bytes)
                        else raw_key
                    )
                    data_str = r_client.get(k)
                    if not data_str:
                        r_client.srem(index_key, k)
                        continue
                    payload = json.loads(data_str)
                    cached_vec = payload.get("vector")
                    if not cached_vec:
                        continue
                    sim = cosine_similarity(query_vector, cached_vec)
                    if sim > highest_sim and sim >= sim_threshold:
                        highest_sim = sim
                        best_match = {
                            "response": payload.get("response"),
                            "similarity_score": round(sim, 4),
                            "matched_query": payload.get("query"),
                            "metadata": payload.get("metadata", {}),
                        }
            except Exception as exc:
                logger.warning("Redis semantic cache read error: %s", exc)

        # Also inspect in-memory store
        self._cleanup_expired_in_memory()
        for q_hash, (c_query, c_vector, c_resp, expires_at, c_meta) in list(
            self._in_memory_store.items()
        ):
            if expires_at and now > expires_at:
                del self._in_memory_store[q_hash]
                continue
            sim = cosine_similarity(query_vector, c_vector)
            if sim > highest_sim and sim >= sim_threshold:
                highest_sim = sim
                best_match = {
                    "response": c_resp,
                    "similarity_score": round(sim, 4),
                    "matched_query": c_query,
                    "metadata": c_meta,
                }

        if best_match is not None:
            self._hits += 1
            logger.info(
                "Semantic cache HIT (similarity=%.4f, matched='%s')",
                highest_sim,
                best_match["matched_query"][:60],
            )
            return best_match

        self._misses += 1
        return None

    def set(
        self,
        query: str,
        response: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a query, its embedding vector, and response in the semantic cache.

        Args:
            query: Input prompt/query string.
            response: Cacheable response data.
            ttl: Time-to-live in seconds.
            metadata: Additional metadata dictionary.

        Returns:
            True upon successful caching.
        """
        if not query or not query.strip():
            return False

        effective_ttl = ttl if ttl is not None else self.default_ttl
        query_vector = self._get_embedding(query.strip())
        now = time.time()
        expires_at = (now + effective_ttl) if effective_ttl > 0 else 0.0
        query_hash = str(abs(hash(query.strip().lower())))

        # Save to in-memory store
        self._in_memory_store[query_hash] = (
            query.strip(),
            query_vector,
            response,
            expires_at,
            metadata or {},
        )

        r_client = self._get_redis_client()
        if r_client is not None:
            try:
                entry_key = f"{self.redis_prefix}:entry:{query_hash}"
                index_key = f"{self.redis_prefix}:index"
                payload = {
                    "query": query.strip(),
                    "vector": query_vector,
                    "response": response,
                    "timestamp": now,
                    "metadata": metadata or {},
                }
                r_client.set(entry_key, json.dumps(payload), ex=effective_ttl)
                r_client.sadd(index_key, entry_key)
            except Exception as exc:
                logger.warning("Redis semantic cache write error: %s", exc)

        return True

    def clear(self) -> int:
        """Clear all semantic cache entries."""
        count = len(self._in_memory_store)
        self._in_memory_store.clear()

        r_client = self._get_redis_client()
        if r_client is not None:
            try:
                index_key = f"{self.redis_prefix}:index"
                keys = r_client.smembers(index_key) or []
                for k in keys:
                    r_client.delete(k)
                r_client.delete(index_key)
            except Exception:
                pass

        return count

    def _cleanup_expired_in_memory(self) -> None:
        """Remove expired in-memory cache entries."""
        now = time.time()
        expired = [
            k
            for k, (_, _, _, exp, _) in self._in_memory_store.items()
            if exp and now > exp
        ]
        for k in expired:
            del self._in_memory_store[k]

    def get_stats(self) -> Dict[str, Any]:
        """Return cache performance statistics."""
        self._cleanup_expired_in_memory()
        total_requests = self._hits + self._misses
        hit_ratio = (self._hits / total_requests) if total_requests > 0 else 0.0
        return {
            "total_in_memory_entries": len(self._in_memory_store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(hit_ratio, 4),
        }


# Default singleton instance
semantic_cache_service = SemanticCacheService()
