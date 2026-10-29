"""
Unit and integration tests for Qdrant Ingestion Pipeline & Metadata Indexing.
"""

from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.config import ARCHITECTURE_GUIDELINES_MD, DATABASE_COMPARISON_PDF, QDRANT_COLLECTION_NAME
from src.ingestion.ingest_qdrant import (
    chunk_text,
    get_qdrant_client,
    ingest_all_documents,
    parse_markdown,
    parse_pdf,
    search_documents,
)


def test_chunk_text_logic():
    """Verify sliding-window chunking logic with overlap."""
    sample = "Word " * 120  # 600 characters
    chunks = chunk_text(sample, chunk_size=200, overlap=50)

    assert len(chunks) >= 3
    # Verify adjacent chunks share overlap
    assert chunks[0][-30:] in chunks[1] or chunks[1][:30] in chunks[0]

    # Test short and empty inputs
    assert chunk_text("") == []
    assert len(chunk_text("Short sentence.")) == 1


def test_parse_pdf_sections():
    """Verify PDF parser extracts sections with headings and page numbers."""
    sections = parse_pdf(DATABASE_COMPARISON_PDF)
    assert len(sections) >= 4, "PDF should yield at least 4 primary sections"

    section_titles = [s["section"] for s in sections]
    assert any("Multi-Tenant" in t or "Isolation" in t for t in section_titles)
    assert all(s["doc_type"] == "pdf" for s in sections)
    assert all(len(s["text"]) > 50 for s in sections)


def test_parse_markdown_sections():
    """Verify Markdown parser segments content by '## ' headings."""
    sections = parse_markdown(ARCHITECTURE_GUIDELINES_MD)
    assert len(sections) >= 3

    section_titles = [s["section"] for s in sections]
    assert any("Data Store Requirements" in t for t in section_titles)
    assert any("Performance & Scalability" in t for t in section_titles)
    assert all(s["doc_type"] == "guideline" for s in sections)


def test_ingestion_pipeline_execution():
    """Verify that ingest_all_documents indexes all chunks into Qdrant."""
    total_indexed = ingest_all_documents(force_recreate=True)
    assert total_indexed >= 25, f"Expected at least 25 chunks, got {total_indexed}"

    client = get_qdrant_client()
    collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
    assert collection_info.points_count >= 25


def test_semantic_search_accuracy():
    """Verify semantic search retrieves relevant chunks with high cosine similarity."""
    results = search_documents(query="How does PostgreSQL handle multi-tenant isolation and RLS?", limit=3)
    assert len(results) > 0

    top_result = results[0]
    assert top_result.score > 0.65, f"Expected high cosine similarity score, got {top_result.score}"
    assert "payload" in dir(top_result)
    assert "content" in top_result.payload
    content = top_result.payload["content"].lower()
    assert "postgresql" in content or "tenant" in content or "isolation" in content


def test_metadata_filtering_guidelines_only():
    """Verify metadata filtering strictly isolates guideline documents."""
    guideline_filter = Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value="guideline"))])
    results = search_documents(
        query="What are the mandatory ACID and data sovereignty rules?", query_filter=guideline_filter, limit=4
    )

    assert len(results) > 0
    for r in results:
        assert r.payload["doc_type"] == "guideline"
        assert r.payload["source_file"] == "architecture_guidelines.md"


def test_metadata_filtering_pdf_only():
    """Verify metadata filtering strictly isolates PDF documents."""
    pdf_filter = Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value="pdf"))])
    results = search_documents(
        query="PostgreSQL vs MongoDB throughput and latency comparison", query_filter=pdf_filter, limit=4
    )

    assert len(results) > 0
    for r in results:
        assert r.payload["doc_type"] == "pdf"
        assert r.payload["source_file"] == "database_comparison.pdf"


def test_ingestion_idempotency():
    """Verify re-running ingestion does not duplicate vectors."""
    client = get_qdrant_client()
    initial_count = client.get_collection(QDRANT_COLLECTION_NAME).points_count

    # Re-run ingestion with force_recreate=False (upsert updates existing points)
    second_count = ingest_all_documents(force_recreate=False)
    assert second_count == initial_count
