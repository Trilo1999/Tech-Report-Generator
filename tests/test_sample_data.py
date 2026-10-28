"""Unit tests to validate integrity and schema of all 5 synthetic sample datasets."""

import json
import pandas as pd
from pypdf import PdfReader
from src.config import (
    BENCHMARK_CSV,
    CLOUD_PRICING_JSON,
    RESEARCH_SOURCES_JSON,
    ARCHITECTURE_GUIDELINES_MD,
    DATABASE_COMPARISON_PDF,
)


def test_database_comparison_pdf_validity():
    """Verify that database_comparison.pdf exists, is non-empty, and has multiple readable pages."""
    assert DATABASE_COMPARISON_PDF.is_file()
    reader = PdfReader(str(DATABASE_COMPARISON_PDF))
    assert len(reader.pages) >= 2, "PDF should contain multiple pages of comparative analysis"

    # Verify key architectural terminology appears in extracted text
    full_text = " ".join([page.extract_text() or "" for page in reader.pages])
    assert "PostgreSQL" in full_text
    assert "MongoDB" in full_text
    assert "multi-tenant" in full_text.lower() or "isolation" in full_text.lower()
    assert "ACID" in full_text


def test_benchmark_results_csv_validity():
    """Verify that benchmark_results.csv contains valid latency and throughput metrics."""
    assert BENCHMARK_CSV.is_file()
    df = pd.read_csv(BENCHMARK_CSV)

    # Check required columns
    expected_cols = {"database", "operation", "latency_ms", "throughput_ops_sec", "concurrency_level", "data_size_gb"}
    assert expected_cols.issubset(set(df.columns))

    # Check row counts and null values
    assert len(df) >= 20, "Should have at least 20 benchmark records"
    assert df["latency_ms"].isnull().sum() == 0
    assert df["throughput_ops_sec"].isnull().sum() == 0

    # Check database coverage
    databases = set(df["database"].unique())
    assert "PostgreSQL" in databases
    assert "MongoDB" in databases

    # Validate numeric realism
    assert (df["latency_ms"] > 0).all()
    assert (df["throughput_ops_sec"] > 0).all()


def test_cloud_pricing_json_validity():
    """Verify cloud_pricing.json contains required pricing tiers and positive rates."""
    assert CLOUD_PRICING_JSON.is_file()
    with open(CLOUD_PRICING_JSON, "r", encoding="utf-8") as f:
        pricing = json.load(f)

    # Check top-level keys
    for key in ["compute", "storage", "backup", "support"]:
        assert key in pricing

    # Verify both databases are represented in compute and storage
    for db in ["postgresql", "mongodb"]:
        assert db in pricing["compute"]
        assert pricing["compute"][db]["price_per_hour"] > 0
        assert db in pricing["storage"]
        assert pricing["storage"][db]["price_per_gb_month"] > 0


def test_research_sources_json_validity():
    """Verify research_sources.json contains valid sources with metadata and reliability scores."""
    assert RESEARCH_SOURCES_JSON.is_file()
    with open(RESEARCH_SOURCES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "sources" in data
    sources = data["sources"]
    assert len(sources) >= 5, "Should provide at least 5 external sources"

    for s in sources:
        assert "id" in s and s["id"].startswith("EXT-")
        assert "title" in s and len(s["title"]) > 5
        assert "url" in s and s["url"].startswith("http")
        assert "snippet" in s and len(s["snippet"]) > 20
        assert 0.0 <= s["reliability_score"] <= 1.0


def test_architecture_guidelines_md_validity():
    """Verify architecture_guidelines.md contains mandatory internal compliance standards."""
    assert ARCHITECTURE_GUIDELINES_MD.is_file()
    content = ARCHITECTURE_GUIDELINES_MD.read_text(encoding="utf-8")

    assert len(content) > 1000
    assert "ACID Compliance" in content
    assert "Data Sovereignty" in content
    assert "Tenant Isolation" in content
    assert "Architecture Decision Record" in content or "ADR" in content
