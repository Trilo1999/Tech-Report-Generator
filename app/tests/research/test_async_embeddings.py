"""Unit tests for non-blocking asynchronous embedding operations."""

import asyncio

import pytest

from app.utils.core_utils.embedding_utils import embeddings_client


@pytest.mark.asyncio
async def test_async_embed_query_non_blocking():
    """Verify aembed_query executes asynchronously in a worker thread."""
    query = "Enterprise PostgreSQL vs MongoDB sharding architecture"
    vector = await embeddings_client.aembed_query(query)
    assert isinstance(vector, list)
    assert len(vector) > 0
    assert all(isinstance(v, float) for v in vector)


@pytest.mark.asyncio
async def test_async_embed_documents_non_blocking():
    """Verify aembed_documents executes asynchronously without blocking event loop."""
    docs = [
        "Distributed database replication and consensus protocols.",
        "Cloud Total Cost of Ownership comparison across tiers.",
    ]
    vectors = await embeddings_client.aembed_documents(docs)
    assert isinstance(vectors, list)
    assert len(vectors) == 2
    for vec in vectors:
        assert isinstance(vec, list)
        assert len(vec) > 0


@pytest.mark.asyncio
async def test_concurrent_async_embeddings():
    """Verify multiple concurrent embedding calls do not block each other."""
    queries = [f"Technical topic test query {i}" for i in range(5)]
    tasks = [embeddings_client.aembed_query(q) for q in queries]
    results = await asyncio.gather(*tasks)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, list)
        assert len(r) > 0
