"""
Comprehensive test suite for the 5 research, analytical, and export tools.
"""

from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfReader

from app.tools import (
    analyze_csv,
    calculate_cost,
    generate_report,
    search_external_sources,
    search_internal_documents,
)


# ────────────────────────────────────────────────────────────
# 1. Internal Search Tool Tests
# ────────────────────────────────────────────────────────────
def test_search_internal_documents_basic():
    """Verify semantic retrieval against Qdrant collection."""
    results = search_internal_documents(
        query="How does PostgreSQL handle multi-tenant isolation?", limit=3
    )
    assert len(results) > 0
    top = results[0]

    assert top["source_id"].startswith("QDR-")
    assert top["source_type"] == "internal_qdrant"
    assert top["reliability_score"] == 1.0
    assert top["similarity_score"] > 0.3
    assert "metadata" in top
    assert len(top["content"]) > 30


def test_search_internal_documents_with_filter():
    """Verify metadata filtering strictly restricts results."""
    # Filter for guideline documents only
    guideline_results = search_internal_documents(
        query="ACID compliance and data sovereignty requirements",
        filters={"doc_type": "guideline"},
        limit=3,
    )
    assert len(guideline_results) > 0
    for r in guideline_results:
        assert r["metadata"]["doc_type"] == "guideline"
        assert "architecture_guidelines.md" in r["metadata"]["source_file"]

    # Filter for PDF documents only
    pdf_results = search_internal_documents(
        query="B-tree index types and query planner comparison",
        filters={"doc_type": "pdf"},
        limit=3,
    )
    assert len(pdf_results) > 0
    for r in pdf_results:
        assert r["metadata"]["doc_type"] == "pdf"
        assert "database_comparison.pdf" in r["metadata"]["source_file"]


def test_search_internal_documents_empty_query():
    """Verify empty query returns empty list without error."""
    assert search_internal_documents(query="") == []
    assert search_internal_documents(query="   ") == []


# ────────────────────────────────────────────────────────────
# 2. External Search Tool Tests
# ────────────────────────────────────────────────────────────
def test_search_external_sources_relevance():
    """Verify keyword and topic matching on external publications."""
    results = search_external_sources(query="PostgreSQL vs MongoDB trade-offs", limit=2)
    assert len(results) > 0

    top = results[0]
    assert top["source_id"].startswith("EXT-")
    assert top["source_type"] == "external_mock"
    assert top["reliability_score"] >= 0.5
    assert "url" in top and top["url"].startswith("http")
    assert "date" in top


def test_search_external_sources_reliability_filter():
    """Verify min_reliability filtering."""
    high_rel_results = search_external_sources(
        query="compliance sovereignty", min_reliability=0.90
    )
    for r in high_rel_results:
        assert r["reliability_score"] >= 0.90


def test_search_external_sources_empty():
    """Verify empty query handling."""
    assert search_external_sources(query="") == []


# ────────────────────────────────────────────────────────────
# 3. Tabular Benchmark Analysis Tests
# ────────────────────────────────────────────────────────────
def test_analyze_csv_summary_stats():
    """Verify summary_stats operation computes exact mean/p95 numbers."""
    result = analyze_csv(operation="summary_stats")
    assert result["source_id"] == "CSV-01"
    assert result["source_type"] == "tabular_csv"

    data = result["data"]
    assert "PostgreSQL" in data and "MongoDB" in data
    assert "read" in data["PostgreSQL"] and "write" in data["PostgreSQL"]

    # Validate numbers match actual benchmark data
    pg_read = data["PostgreSQL"]["read"]
    assert pg_read["mean_latency_ms"] > 0
    assert pg_read["mean_throughput_ops_sec"] > 0
    assert pg_read["sample_count"] > 0


def test_analyze_csv_latency_percentiles():
    """Verify latency_percentiles computes p50, p90, p95, p99."""
    result = analyze_csv(operation="latency_percentiles")
    data = result["data"]

    for db in ["PostgreSQL", "MongoDB"]:
        for op in ["read", "write"]:
            metrics = data[db][op]
            assert metrics["p50_latency_ms"] <= metrics["p95_latency_ms"]
            assert metrics["p95_latency_ms"] <= metrics["p99_latency_ms"]


def test_analyze_csv_concurrency_scaling():
    """Verify concurrency_scaling breaks down metrics by connection tiers."""
    result = analyze_csv(operation="concurrency_scaling")
    data = result["data"]
    assert 50 in data["PostgreSQL"]
    assert 100 in data["PostgreSQL"]
    assert 200 in data["PostgreSQL"]


def test_analyze_csv_invalid_operation():
    """Verify invalid operation raises structured ValueError."""
    with pytest.raises(ValueError, match="Unsupported operation"):
        analyze_csv(operation="non_existent_op")


# ────────────────────────────────────────────────────────────
# 4. Cost Calculator Tests
# ────────────────────────────────────────────────────────────
def test_calculate_cost_standard_12_months():
    """Verify exact formula calculation for 12 months at 500GB."""
    result = calculate_cost(
        config={
            "databases": ["postgresql", "mongodb"],
            "storage_gb": 500,
            "compute_instances": 3,
            "projection_months": 12,
            "include_support": True,
        }
    )
    assert result["source_id"] == "COST-01"
    assert result["source_type"] == "cost_calculation"

    breakdown = result["breakdown"]
    assert "postgresql" in breakdown
    assert "mongodb" in breakdown

    pg = breakdown["postgresql"]
    mongo = breakdown["mongodb"]

    # Verify mathematical formula precision:
    # PG compute: 0.48 * 730 * 3 = 1051.20
    # PG storage: 500 * 0.10 = 50.00
    # PG backup:  500 * 0.021 = 10.50
    # PG support: 100.00
    # PG monthly: 1211.70 -> 12-mo projected: 14540.40
    assert pg["monthly_compute"] == 1051.20
    assert pg["monthly_storage"] == 50.00
    assert pg["monthly_backup"] == 10.50
    assert pg["monthly_support"] == 100.00
    assert pg["total_monthly"] == 1211.70
    assert pg["total_projected"] == 14540.40

    # Mongo compute: 0.52 * 730 * 3 = 1138.80
    # Mongo storage: 500 * 0.25 = 125.00
    # Mongo backup:  500 * 0.025 = 12.50
    # Mongo support: 150.00
    # Mongo monthly: 1426.30 -> 12-mo projected: 17115.60
    assert mongo["monthly_compute"] == 1138.80
    assert mongo["monthly_storage"] == 125.00
    assert mongo["monthly_backup"] == 12.50
    assert mongo["monthly_support"] == 150.00
    assert mongo["total_monthly"] == 1426.30
    assert mongo["total_projected"] == 17115.60

    # Verify comparative delta
    comp = result["comparison"]
    assert comp["cheaper_database"] == "postgresql"
    assert comp["projected_difference_amount"] == 2575.20
    assert comp["savings_percentage"] == round((2575.20 / 17115.60) * 100, 2)


def test_calculate_cost_36_months_revision():
    """Verify 3-year TCO calculation for human-in-the-loop revision scenario."""
    result = calculate_cost(
        config={
            "databases": ["postgresql", "mongodb"],
            "storage_gb": 500,
            "compute_instances": 3,
            "projection_months": 36,
        }
    )
    pg = result["breakdown"]["postgresql"]
    assert pg["total_projected"] == round(pg["total_monthly"] * 36, 2)


# ────────────────────────────────────────────────────────────
# 5. Report Exporter Tests (PDF & DOCX)
# ────────────────────────────────────────────────────────────
def test_generate_report_pdf(tmp_path):
    """Verify PDF export produces valid, readable ReportLab document."""
    mock_content = {
        "title": "PostgreSQL vs MongoDB Technical Evaluation",
        "status": "APPROVED",
        "sections": {
            "Executive Summary": "This report evaluates PostgreSQL and MongoDB for multi-tenant SaaS deployment [EXT-01].",
            "Architecture Comparison": "PostgreSQL uses schema-per-tenant isolation with Row Level Security [QDR-01].",
            "Performance Analysis": "MongoDB showed lower read latency while PostgreSQL had stronger write stability [CSV-01].",
            "Cost Projections": "PostgreSQL offers ~15% lower 12-month TCO [COST-01].",
            "Strategic Recommendation": "PostgreSQL is recommended for ACID and cost compliance.",
        },
        "benchmark_summary": {
            "PostgreSQL": {
                "read": {
                    "mean_latency_ms": 14.0,
                    "p95_latency_ms": 18.4,
                    "mean_throughput_ops_sec": 4350,
                }
            },
            "MongoDB": {
                "read": {
                    "mean_latency_ms": 10.6,
                    "p95_latency_ms": 15.1,
                    "mean_throughput_ops_sec": 5050,
                }
            },
        },
        "unsupported_claims": [
            "Multi-region replication takes < 50ms without active geo-sharding"
        ],
        "cited_sources": [
            {
                "source_id": "QDR-01",
                "title": "database_comparison.pdf",
                "source_type": "Internal Document",
            },
            {
                "source_id": "CSV-01",
                "title": "benchmark_results.csv",
                "source_type": "Tabular Benchmark",
            },
            {
                "source_id": "COST-01",
                "title": "cloud_pricing.json",
                "source_type": "Pricing Calculator",
            },
            {
                "source_id": "EXT-01",
                "title": "Analyst Report 2024",
                "url": "https://example.com/analyst",
            },
        ],
    }

    pdf_path = generate_report(
        mock_content, format="pdf", output_filename="test_report_eval.pdf"
    )
    assert Path(pdf_path).is_file()
    assert Path(pdf_path).stat().st_size > 1000  # Non-trivial PDF binary

    # Verify PDF readability with PyPDF
    reader = PdfReader(pdf_path)
    assert len(reader.pages) >= 1
    extracted = "".join([p.extract_text() or "" for p in reader.pages])
    assert "PostgreSQL vs MongoDB" in extracted
    assert "Executive Summary" in extracted
    assert "[QDR-01]" in extracted
    assert "Unsupported Claims" in extracted or "LIMITATION" in extracted


def test_generate_report_docx():
    """Verify DOCX export produces valid Microsoft Word document."""
    mock_content = {
        "title": "Database Architecture Assessment",
        "sections": {
            "Executive Summary": "Overview of findings [QDR-01].",
            "Recommendations": "Recommendation summary.",
        },
        "unsupported_claims": ["Unverified caching performance under 10k connections"],
        "cited_sources": [{"source_id": "QDR-01", "title": "Internal Doc"}],
    }

    docx_path = generate_report(
        mock_content, format="docx", output_filename="test_report_eval.docx"
    )
    assert Path(docx_path).is_file()
    assert Path(docx_path).stat().st_size > 500

    # Verify DOCX structure
    doc = Document(docx_path)
    text = " ".join([p.text for p in doc.paragraphs])
    assert "Database Architecture Assessment" in text
    assert "Executive Summary" in text
    assert "[QDR-01]" in text


def test_generate_report_invalid_format():
    """Verify invalid export format raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported report export format"):
        generate_report({"title": "Test"}, format="html")


# ────────────────────────────────────────────────────────────
# 6. Tavily Web Search Tool Tests
# ────────────────────────────────────────────────────────────
def test_search_tavily_without_key_graceful_empty(monkeypatch):
    """Verify search_tavily returns empty list gracefully when API key is not set."""
    from app.tools.external_search_tool import search_tavily

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    results = search_tavily("latest ecommerce architecture", limit=2)
    assert results == []


def test_search_tavily_with_mock_client(monkeypatch):
    """Verify search_tavily correctly normalizes Tavily API results into standardized citations."""
    from unittest.mock import MagicMock

    import tavily

    from app.tools.external_search_tool import (
        default_external_search_engine,
        search_tavily_web_tool,
    )

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-mock-test-key")
    monkeypatch.delenv("MOCK_LLM", raising=False)

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Modern Multi-Tenant SaaS Architecture 2026",
                "url": "https://architecture.example.com/saas-multitenant",
                "content": "Row-level security and tenant routing via API gateways maximize tenant density and isolation.",
                "score": 0.94,
            },
            {
                "title": "Scaling E-Commerce Order Pipelines",
                "url": "https://retailtech.example.org/pipelines",
                "content": "Event-driven asynchronous queues decouple inventory reservations from payment settlement.",
                "score": 0.88,
            },
        ]
    }
    monkeypatch.setattr(tavily, "TavilyClient", lambda api_key: mock_client)

    results = default_external_search_engine.search_tavily(
        "saas multi-tenant ecommerce", limit=2
    )
    assert len(results) == 2
    top = results[0]
    assert top["source_id"] == "EXT-TAVILY-01"
    assert top["source_type"] == "external_tavily"
    assert "architecture.example.com" in top["author"]
    assert top["reliability_score"] >= 0.85
    assert "Row-level security" in top["content"]

    # Also test the LangChain @tool wrapper
    tool_results = search_tavily_web_tool.invoke(
        {"query": "saas multi-tenant ecommerce", "limit": 2}
    )
    assert len(tool_results) == 2
    assert tool_results[0]["source_id"] == "EXT-TAVILY-01"
