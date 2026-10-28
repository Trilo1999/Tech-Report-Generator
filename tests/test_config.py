"""Unit tests for configuration and environment settings."""

from src.config import (
    settings,
    PROJECT_ROOT,
    DATA_DIR,
    SAMPLE_DATA_DIR,
    REPORTS_DIR,
    BENCHMARK_CSV,
    CLOUD_PRICING_JSON,
    RESEARCH_SOURCES_JSON,
    ARCHITECTURE_GUIDELINES_MD,
    DATABASE_COMPARISON_PDF,
    MAX_RESEARCH_ITERATIONS,
    MIN_SUBQUESTIONS,
)


def test_project_directories_exist():
    """Verify that all core directories exist."""
    assert PROJECT_ROOT.is_dir()
    assert DATA_DIR.is_dir()
    assert SAMPLE_DATA_DIR.is_dir()
    assert REPORTS_DIR.is_dir()


def test_sample_data_file_paths():
    """Verify that all sample data path constants point to expected files."""
    assert BENCHMARK_CSV.name == "benchmark_results.csv"
    assert CLOUD_PRICING_JSON.name == "cloud_pricing.json"
    assert RESEARCH_SOURCES_JSON.name == "research_sources.json"
    assert ARCHITECTURE_GUIDELINES_MD.name == "architecture_guidelines.md"
    assert DATABASE_COMPARISON_PDF.name == "database_comparison.pdf"


def test_workflow_constants():
    """Verify default workflow thresholds satisfy requirements."""
    assert MIN_SUBQUESTIONS >= 3, "Acceptance criteria requires at least 3 subquestions"
    assert MAX_RESEARCH_ITERATIONS >= 1, "Must allow at least one sufficiency loop"


def test_settings_representation():
    """Verify that settings repr outputs readable path diagnostics."""
    repr_str = repr(settings)
    assert "Settings(" in repr_str
    assert "PROJECT_ROOT" in repr_str
    assert "all-MiniLM-L6-v2" in repr_str
