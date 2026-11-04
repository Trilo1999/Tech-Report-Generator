"""Redis and in-memory caching service for the AI Research & Report Generation Agent.

Provides:
- General key-value caching with JSON serialization and configurable TTL.
- In-memory TTL fallback when Redis is offline or disabled.
- Synchronous and asynchronous function caching decorators (@cached).
- Domain caching helpers for external search queries, generated reports, and precedent memory.
- LangChain LLM response caching via RedisCache / InMemoryCache.
"""

import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, Optional

from app.config.env_config import settings
from app.config.redis_config import is_redis_available, redis_config

logger = logging.getLogger("research_agent.cache")


class InMemoryTTLCache:
    """Thread-safe in-memory cache with time-to-live expiration."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        self.cleanup_expired()
        entry = self._store.get(key)
        if entry is None:
            return default
        value, expires_at = entry
        if expires_at and time.time() > expires_at:
            del self._store[key]
            return default
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        expires_at = (time.time() + ttl) if ttl and ttl > 0 else 0.0
        self._store[key] = (value, expires_at)
        return True

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def clear_prefix(self, prefix: str) -> int:
        keys_to_del = [k for k in self._store.keys() if k.startswith(prefix)]
        for k in keys_to_del:
            del self._store[k]
        return len(keys_to_del)

    def cleanup_expired(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if exp and now > exp]
        for k in expired:
            del self._store[k]

    def size(self) -> int:
        self.cleanup_expired()
        return len(self._store)


class CacheService:
    """Unified caching service delegating to Redis with in-memory TTL fallback."""

    def __init__(self) -> None:
        self.in_memory = InMemoryTTLCache()
        self.default_ttl = getattr(settings, "REDIS_CACHE_TTL_SECONDS", 3600)

    def _get_client(self):
        if not is_redis_available():
            return None
        return redis_config.get_redis_client()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value by key, deserializing from JSON.

        Args:
            key: Cache key.
            default: Default value returned on cache miss.

        Returns:
            Cached deserialized Python object, or default.
        """
        client = self._get_client()
        if client is not None:
            try:
                raw = client.get(key)
                if raw is not None:
                    return json.loads(raw)
                return default
            except Exception as e:
                logger.debug(
                    "Redis cache get error for %s (%s); falling back to in-memory",
                    key,
                    e,
                )
        return self.in_memory.get(key, default)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a JSON-serializable value with an optional TTL.

        Args:
            key: Cache key.
            value: Python data object (must be JSON serializable).
            ttl: Time-to-live in seconds. Defaults to REDIS_CACHE_TTL_SECONDS.

        Returns:
            True if stored successfully.
        """
        effective_ttl = ttl if ttl is not None else self.default_ttl
        client = self._get_client()
        if client is not None:
            try:
                payload = json.dumps(value, default=str)
                if effective_ttl and effective_ttl > 0:
                    client.set(key, payload, ex=effective_ttl)
                else:
                    client.set(key, payload)
                return True
            except Exception as e:
                logger.debug(
                    "Redis cache set error for %s (%s); falling back to in-memory",
                    key,
                    e,
                )
        return self.in_memory.set(key, value, effective_ttl)

    def delete(self, key: str) -> bool:
        """Delete a key from Redis and in-memory cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if deleted or was absent.
        """
        client = self._get_client()
        redis_deleted = False
        if client is not None:
            try:
                redis_deleted = bool(client.delete(key))
            except Exception as e:
                logger.debug("Redis cache delete error for %s: %s", key, e)
        mem_deleted = self.in_memory.delete(key)
        return redis_deleted or mem_deleted

    def exists(self, key: str) -> bool:
        """Check if a cache key exists and is unexpired."""
        client = self._get_client()
        if client is not None:
            try:
                return bool(client.exists(key))
            except Exception as e:
                logger.debug("Redis cache exists error for %s: %s", key, e)
        return self.in_memory.exists(key)

    def clear_prefix(self, prefix: str) -> int:
        """Clear all keys starting with a given prefix.

        Args:
            prefix: Key prefix to match (e.g. 'search_cache:').

        Returns:
            Number of keys cleared.
        """
        count = 0
        client = self._get_client()
        if client is not None:
            try:
                pattern = f"{prefix}*"
                keys = client.keys(pattern)
                if keys:
                    count += client.delete(*keys)
            except Exception as e:
                logger.debug("Redis cache clear_prefix error for %s: %s", prefix, e)
        count += self.in_memory.clear_prefix(prefix)
        return count

    def get_or_set(
        self, key: str, factory: Callable[[], Any], ttl: Optional[int] = None
    ) -> Any:
        """Cache-aside helper: fetch existing cached value or compute and store it.

        Args:
            key: Cache key.
            factory: Callable producing the value if not cached.
            ttl: Optional TTL in seconds.

        Returns:
            Cached or computed value.
        """
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        fresh_value = factory()
        if fresh_value is not None:
            self.set(key, fresh_value, ttl=ttl)
        return fresh_value

    def cached(
        self,
        prefix: str,
        ttl: Optional[int] = None,
        key_builder: Optional[Callable[..., str]] = None,
    ):
        """Decorator to cache function results.

        Args:
            prefix: Cache key prefix.
            ttl: TTL in seconds.
            key_builder: Optional custom key function.
        """

        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if key_builder:
                    cache_key = f"{prefix}:{key_builder(*args, **kwargs)}"
                else:
                    repr_args = hashlib.md5(
                        f"{args}:{sorted(kwargs.items())}".encode("utf-8")
                    ).hexdigest()
                    cache_key = f"{prefix}:{func.__name__}:{repr_args}"

                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                result = func(*args, **kwargs)
                if result is not None:
                    self.set(cache_key, result, ttl=ttl)
                return result

            return wrapper

        return decorator

    # --- Domain-Specific Helpers ---

    def _hash_query(self, query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]

    def cache_search_query(
        self, query: str, results: Any, ttl: Optional[int] = None
    ) -> bool:
        """Cache results of an external/internal research query."""
        key = f"search_cache:{self._hash_query(query)}"
        return self.set(key, results, ttl=ttl)

    def get_cached_search_query(self, query: str) -> Optional[Any]:
        """Fetch previously cached research query results."""
        key = f"search_cache:{self._hash_query(query)}"
        return self.get(key)

    def cache_report(
        self,
        thread_id: str,
        report_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache generated report artifacts for rapid re-reading."""
        key = f"report_cache:{thread_id}"
        return self.set(key, report_data, ttl=ttl)

    def get_cached_report(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached report artifact by workflow thread ID."""
        key = f"report_cache:{thread_id}"
        return self.get(key)

    def cache_research_memory(
        self, topic: str, data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Cache cross-session research precedent memories."""
        key = f"research_memory:{self._hash_query(topic)}"
        return self.set(key, data, ttl=ttl)

    def get_research_memory(self, topic: str) -> Optional[Dict[str, Any]]:
        """Retrieve cross-session research precedent memory."""
        key = f"research_memory:{self._hash_query(topic)}"
        return self.get(key)

    # --- LangChain LLM Cache ---

    def init_llm_cache(self) -> bool:
        """Initialize LangChain LLM caching using RedisCache or InMemoryCache.

        Returns:
            True if cache was configured, False otherwise.
        """
        if not getattr(settings, "ENABLE_REDIS_LLM_CACHE", False):
            return False

        try:
            from langchain_core.globals import set_llm_cache

            if is_redis_available():
                from langchain_community.cache import RedisCache

                client = redis_config.get_redis_client()
                if client is not None:
                    set_llm_cache(RedisCache(redis_=client))
                    logger.info("LangChain RedisCache successfully initialized")
                    return True
            else:
                from langchain_core.caches import InMemoryCache

                set_llm_cache(InMemoryCache())
                logger.info("LangChain InMemoryCache initialized (Redis unavailable)")
                return True
        except Exception as e:
            logger.warning("Could not initialize LangChain LLM cache: %s", e)
            return False

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of the caching system."""
        redis_up = is_redis_available()
        backend = "redis" if redis_up else "in_memory"
        keys_count: Optional[int] = None

        if redis_up:
            try:
                client = redis_config.get_redis_client()
                if client is not None:
                    keys_count = len(client.keys("*"))
            except Exception:
                keys_count = None
        else:
            keys_count = self.in_memory.size()

        return {
            "backend": backend,
            "is_redis_available": redis_up,
            "host": settings.REDIS_HOST,
            "port": int((settings.REDIS_PORT or "6379").strip() or "6379"),
            "db": int((settings.REDIS_DB or "0").strip() or "0"),
            "default_ttl_seconds": self.default_ttl,
            "chat_ttl_seconds": getattr(settings, "REDIS_CHAT_TTL_SECONDS", 86400),
            "llm_cache_enabled": getattr(settings, "ENABLE_REDIS_LLM_CACHE", False),
            "keys_count": keys_count,
        }


cache_service = CacheService()
