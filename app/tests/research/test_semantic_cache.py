"""Unit tests for semantic vector response caching with similarity thresholds."""

from app.services.core_services.semantic_cache_service import (
    SemanticCacheService,
    cosine_similarity,
)


def test_cosine_similarity_calculation():
    """Verify vector cosine similarity arithmetic."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == 0.0

    v4 = [1.0, 1.0, 0.0]
    sim = cosine_similarity(v1, v4)
    assert 0.70 < sim < 0.71


def test_semantic_cache_hit_on_semantically_similar_query():
    """Verify semantic cache hits when a query with equivalent meaning is queried."""
    cache = SemanticCacheService(default_threshold=0.85)
    cache.clear()

    # Pre-seed cache with detailed research result
    sample_response = {
        "summary": "PostgreSQL provides transactional integrity via WAL and ACID MVCC.",
        "p95_latency_ms": 11.2,
    }
    cache.set(
        query="What is the architectural reliability and latency of PostgreSQL?",
        response=sample_response,
    )

    # Query with slightly different phrasing but identical meaning
    similar_query = (
        "What is the architectural reliability and p95 latency of PostgreSQL?"
    )
    match = cache.get(similar_query, threshold=0.85)

    assert match is not None
    assert match["response"]["p95_latency_ms"] == 11.2
    assert match["similarity_score"] >= 0.85


def test_semantic_cache_miss_on_unrelated_query():
    """Verify semantic cache returns None when query topic differs."""
    cache = SemanticCacheService(default_threshold=0.85)
    cache.clear()

    cache.set(
        query="PostgreSQL ACID transaction isolation",
        response={"topic": "PostgreSQL"},
    )

    unrelated_query = "How to style React buttons using Tailwind CSS?"
    match = cache.get(unrelated_query, threshold=0.85)

    assert match is None


def test_semantic_cache_clear_and_stats():
    """Verify cache statistics and clearing mechanism."""
    cache = SemanticCacheService()
    cache.clear()

    cache.set("Sample query A", {"data": 1})
    cache.set("Sample query B", {"data": 2})

    stats = cache.get_stats()
    assert stats["total_in_memory_entries"] == 2

    cache.clear()
    stats_after = cache.get_stats()
    assert stats_after["total_in_memory_entries"] == 0
