"""Unit tests for HyDE (Hypothetical Document Embeddings) and Multi-Query Expansion."""

from app.utils.core_utils.hyde_utils import HyDEEngine


def test_expand_queries_generates_diverse_technical_angles():
    """Verify expand_queries decomposes base query into multiple dimensions."""
    query = "PostgreSQL sharding and partition performance"
    expanded = HyDEEngine.expand_queries(query, num_queries=3)

    assert len(expanded) >= 3
    assert query in expanded
    assert any("latency" in q.lower() or "throughput" in q.lower() for q in expanded)
    assert any(
        "architectural" in q.lower() or "isolation" in q.lower() for q in expanded
    )


def test_generate_hypothetical_document_creates_domain_content():
    """Verify generate_hypothetical_document returns a detailed technical answer passage."""
    query = "MongoDB write concern and replica set failover time"
    hyde_doc = HyDEEngine.generate_hypothetical_document(query)

    assert isinstance(hyde_doc, str)
    assert len(hyde_doc) > 60
    assert "MongoDB" in hyde_doc or "failover" in hyde_doc or "concurrency" in hyde_doc


def test_retrieve_with_hyde_and_multi_query_reciprocal_rank_fusion():
    """Verify multi-query and HyDE search aggregates and fuses candidate rankings via RRF."""

    # Mock retriever function returning simulated ranked results
    def mock_retriever(query: str, limit: int = 4, **kwargs):
        if "trade-offs" in query:
            return [
                {
                    "source_id": "QDR-01",
                    "content": "PostgreSQL architecture standards.",
                },
                {"source_id": "QDR-02", "content": "Data modeling best practices."},
            ]
        elif "Technical Architecture Reference" in query:  # HyDE match
            return [
                {
                    "source_id": "QDR-03",
                    "content": "Clustering and replica failover latency.",
                },
                {
                    "source_id": "QDR-01",
                    "content": "PostgreSQL architecture standards.",
                },
            ]
        return [
            {"source_id": "QDR-01", "content": "PostgreSQL architecture standards."},
            {"source_id": "QDR-04", "content": "General system guidelines."},
        ]

    fused = HyDEEngine.retrieve_with_hyde_and_multi_query(
        retriever_func=mock_retriever,
        query="PostgreSQL database scaling",
        limit=3,
        use_hyde=True,
        use_multi_query=True,
    )

    assert isinstance(fused, list)
    assert len(fused) <= 3
    # QDR-01 was present across multiple queries so it should rank highest with highest rrf_score
    top_doc = fused[0]
    assert top_doc["source_id"] == "QDR-01"
    assert "rrf_score" in top_doc
    assert top_doc["rrf_score"] > 0.0
