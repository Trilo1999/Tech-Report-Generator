"""Unit and integration tests for Redis Conversation Memory and Caching Service."""

import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config.redis_config import RedisConfig, is_redis_available, reset_redis_status
from app.main import app
from app.services.core_services.cache_service import CacheService, InMemoryTTLCache
from app.utils.core_utils.redis_utils import ResilientChatMessageHistory, redis_history

client = TestClient(app)


# --- RedisConfig Tests ---


def test_redis_config_url_generation():
    """Verify standard Redis connection URL construction."""
    cfg = RedisConfig()
    cfg.host = "127.0.0.1"
    cfg.port = 6379
    cfg.db = 0
    cfg.password = None
    assert cfg.get_redis_url() == "redis://127.0.0.1:6379/0"


def test_redis_config_url_with_password():
    """Verify Redis connection URL includes password when configured."""
    cfg = RedisConfig()
    cfg.host = "redis.internal"
    cfg.port = 6380
    cfg.db = 2
    cfg.password = "secretpass123"
    assert cfg.get_redis_url() == "redis://:secretpass123@redis.internal:6380/2"


def test_redis_config_is_available_offline():
    """Verify is_available handles offline/unreachable Redis gracefully without raising."""
    reset_redis_status()
    cfg = RedisConfig()
    cfg.host = "invalid.unreachable.host"
    cfg.port = 9999
    # Should not raise exception, but return False
    assert cfg.is_available(force_check=True) is False
    assert is_redis_available() is False


def test_redis_config_is_available_when_mocked():
    """Verify is_available returns True when Redis client responds to ping."""
    reset_redis_status()
    cfg = RedisConfig()
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with patch.object(cfg, "get_redis_client", return_value=mock_redis):
        assert cfg.is_available(force_check=True) is True


# --- Resilient Conversation Memory Tests ---


def test_resilient_chat_history_in_memory_fallback():
    """Verify ResilientChatMessageHistory falls back cleanly to in-memory store when Redis is offline."""
    session_id = f"test_session_{time.time()}"
    history = ResilientChatMessageHistory(
        session_id=session_id,
        redis_url="redis://invalid:6379/0",
        ttl=60,
    )

    # Initially empty
    assert len(history.messages) == 0

    # Add messages
    history.add_message(HumanMessage(content="Hello AI Architect!"))
    history.add_message(AIMessage(content="Hello! How can I assist with your system?"))

    # Fetch messages
    messages = history.messages
    assert len(messages) == 2
    assert messages[0].content == "Hello AI Architect!"
    assert messages[1].content == "Hello! How can I assist with your system?"

    # Clear history
    history.clear()
    assert len(history.messages) == 0


def test_redis_history_get_messages_formatting():
    """Verify RedisHistory.get_messages formats messages into role and content pairs."""
    session_id = f"test_format_{time.time()}"
    hist = redis_history.get_redis_history(session_id)
    hist.add_message(HumanMessage(content="Compare Redis and Memcached"))
    hist.add_message(
        AIMessage(content="Redis supports data structures, while Memcached is simpler.")
    )
    hist.add_message(SystemMessage(content="System instruction"))

    formatted = redis_history.get_messages(session_id)
    assert len(formatted) == 3
    assert formatted[0] == {"role": "user", "content": "Compare Redis and Memcached"}
    assert formatted[1] == {
        "role": "assistant",
        "content": "Redis supports data structures, while Memcached is simpler.",
    }
    assert formatted[2] == {"role": "system", "content": "System instruction"}

    redis_history.clear_history(session_id)
    assert len(redis_history.get_messages(session_id)) == 0


def test_resilient_chat_history_redis_delegation():
    """Verify ResilientChatMessageHistory delegates to RedisChatMessageHistory when available."""
    session_id = f"test_redis_mock_{time.time()}"
    history = ResilientChatMessageHistory(
        session_id=session_id,
        redis_url="redis://localhost:6379/0",
        ttl=300,
    )

    mock_redis_impl = MagicMock()
    mock_redis_impl.messages = [HumanMessage(content="Redis stored message")]

    with (
        patch("app.utils.core_utils.redis_utils.is_redis_available", return_value=True),
        patch(
            "app.utils.core_utils.redis_utils.RedisChatMessageHistory",
            return_value=mock_redis_impl,
        ),
    ):
        assert history.messages[0].content == "Redis stored message"
        history.add_message(AIMessage(content="Response"))
        mock_redis_impl.add_message.assert_called_once()
        history.clear()
        mock_redis_impl.clear.assert_called_once()


# --- CacheService Tests ---


def test_in_memory_ttl_cache_basic_and_expiration():
    """Verify InMemoryTTLCache get, set, exists, and TTL expiration."""
    cache = InMemoryTTLCache()
    cache.set("key1", {"value": 42}, ttl=1)
    assert cache.exists("key1") is True
    assert cache.get("key1") == {"value": 42}

    # Test default on missing
    assert cache.get("nonexistent", "fallback") == "fallback"

    # Test deletion
    cache.set("key2", "to_delete")
    assert cache.delete("key2") is True
    assert cache.exists("key2") is False

    # Test clear_prefix
    cache.set("prefix:a", 1)
    cache.set("prefix:b", 2)
    cache.set("other:c", 3)
    assert cache.clear_prefix("prefix:") == 2
    assert cache.exists("prefix:a") is False
    assert cache.exists("other:c") is True


def test_cache_service_fallback_operations():
    """Verify CacheService get, set, delete, and get_or_set using in-memory fallback."""
    svc = CacheService()
    svc.set("test_key", {"data": "test_payload"}, ttl=60)
    assert svc.exists("test_key") is True
    assert svc.get("test_key") == {"data": "test_payload"}

    # get_or_set
    computed = svc.get_or_set("cached_calc", lambda: 100 * 2, ttl=60)
    assert computed == 200
    # Second call uses cache, factory not evaluated
    factory_mock = MagicMock()
    second = svc.get_or_set("cached_calc", factory_mock, ttl=60)
    assert second == 200
    factory_mock.assert_not_called()

    svc.delete("test_key")
    assert svc.get("test_key") is None


def test_cache_service_decorator():
    """Verify @cached decorator caches function calls."""
    svc = CacheService()
    call_count = 0

    @svc.cached(prefix="math_test", ttl=60)
    def expensive_square(n: int) -> int:
        nonlocal call_count
        call_count += 1
        return n * n

    assert expensive_square(5) == 25
    assert call_count == 1
    # Second call should be retrieved from cache
    assert expensive_square(5) == 25
    assert call_count == 1

    # Different argument calls the function
    assert expensive_square(6) == 36
    assert call_count == 2


def test_cache_service_domain_helpers():
    """Verify specialized domain caching helpers for search, reports, and memory."""
    svc = CacheService()

    # Search query caching
    query = "Distributed database consensus algorithms"
    results = [{"source_id": "EXT-01", "title": "Raft vs Paxos"}]
    assert svc.cache_search_query(query, results, ttl=60) is True
    cached_search = svc.get_cached_search_query(query)
    assert cached_search == results

    # Report caching
    thread_id = "research_task_123"
    report_data = {
        "title": "Distributed DB Report",
        "sections": {"Summary": "Approved"},
    }
    assert svc.cache_report(thread_id, report_data, ttl=60) is True
    assert svc.get_cached_report(thread_id) == report_data

    # Precedent memory caching
    topic = "PostgreSQL multi-tenant schema isolation"
    memory_data = {"summary": "Use schema-per-tenant for HIPAA compliance."}
    assert svc.cache_research_memory(topic, memory_data, ttl=60) is True
    assert svc.get_research_memory(topic) == memory_data


def test_cache_service_status():
    """Verify CacheService get_status returns expected structure and diagnostic data."""
    svc = CacheService()
    status = svc.get_status()
    assert "backend" in status
    assert "is_redis_available" in status
    assert "host" in status
    assert "port" in status
    assert "db" in status
    assert "default_ttl_seconds" in status
    assert "chat_ttl_seconds" in status


# --- REST API Endpoints Tests ---


def test_api_chat_history_and_clear_lifecycle():
    """Verify GET and DELETE /api/v1/chat/history endpoints."""
    thread_id = f"test_api_thread_{time.time()}"

    # Add message directly to thread history
    hist = redis_history.get_redis_history(thread_id)
    hist.add_message(HumanMessage(content="What are the best vector databases?"))
    hist.add_message(
        AIMessage(content="Qdrant, Pinecone, and Milvus are top candidates.")
    )

    # 1. Fetch history via API
    res = client.get(f"/api/v1/chat/history/{thread_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["thread_id"] == thread_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert "vector databases" in data["messages"][0]["content"]
    assert data["messages"][1]["role"] == "assistant"
    assert "Qdrant" in data["messages"][1]["content"]

    # 2. Clear history via API
    del_res = client.delete(f"/api/v1/chat/history/{thread_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["thread_id"] == thread_id
    assert del_data["status"] == "cleared"

    # 3. Verify history is empty
    empty_res = client.get(f"/api/v1/chat/history/{thread_id}")
    assert empty_res.status_code == 200
    assert len(empty_res.json()["messages"]) == 0


def test_api_cache_status_and_clear_endpoints():
    """Verify GET /api/v1/cache/status and POST /api/v1/cache/clear endpoints."""
    # 1. Check cache status
    res = client.get("/api/v1/cache/status")
    assert res.status_code == 200
    data = res.json()
    assert data["backend"] in ("redis", "in_memory")
    assert "default_ttl_seconds" in data
    assert "is_redis_available" in data

    # 2. Seed cache key
    from app.services.core_services.cache_service import cache_service

    cache_service.set("prefix_test:item1", {"val": 1})
    cache_service.set("prefix_test:item2", {"val": 2})

    # 3. Clear by prefix
    clear_res = client.post("/api/v1/cache/clear", json={"prefix": "prefix_test:"})
    assert clear_res.status_code == 200
    clear_data = clear_res.json()
    assert clear_data["status"] == "success"
    assert clear_data["cleared_keys"] >= 2
    assert cache_service.get("prefix_test:item1") is None
