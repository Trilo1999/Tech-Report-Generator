"""Unit tests for RAG Faithfulness and Hallucination Verification Engine."""

from app.utils.core_utils.faithfulness_verifier import (
    FaithfulnessVerifier,
    verify_draft_faithfulness,
)


def test_faithfulness_verifier_with_grounded_citations():
    """Verify clean report with valid citations achieves high faithfulness score."""
    sections = {
        "Executive Summary": (
            "Enterprise database evaluation indicates strong write scaling [QDR-01: Architectural Guidelines]. "
            "Empirical telemetry across concurrent connections demonstrates low p95 latency [CSV-01: Benchmarks]."
        ),
        "Cost Analysis": (
            "The 12-month cloud TCO model yields estimated infrastructure costs of $1,200/mo [COST-01: Cloud Model]."
        ),
    }
    evidence_list = [
        {
            "source_id": "QDR-01",
            "title": "Architectural Guidelines",
            "content": "Guidelines for enterprise database scaling and partitioning.",
        },
        {
            "source_id": "CSV-01",
            "title": "Benchmarks",
            "content": "Benchmark results under 100 concurrent connections.",
        },
        {
            "source_id": "COST-01",
            "title": "Cloud Model",
            "content": "Cost projection for AWS and GCP infrastructure.",
        },
    ]

    result = verify_draft_faithfulness(sections, evidence_list)

    assert result["faithfulness_score"] == 1.0
    assert result["hallucination_detected"] is False
    assert len(result["unsupported_claims"]) == 0
    assert len(result["invalid_citations"]) == 0


def test_faithfulness_verifier_detects_invalid_citation():
    """Verify citing a non-existent source triggers hallucination flag."""
    sections = {
        "Executive Summary": (
            "System provides automatic zero-downtime shard migration [NONEXISTENT-99: Ghost Whitepaper]."
        )
    }
    evidence_list = [
        {
            "source_id": "QDR-01",
            "title": "Real Source",
            "content": "Valid database specs.",
        }
    ]

    result = verify_draft_faithfulness(sections, evidence_list)

    assert result["hallucination_detected"] is True
    assert "NONEXISTENT-99" in result["invalid_citations"]
    assert any("NONEXISTENT-99" in c for c in result["unsupported_claims"])


def test_faithfulness_verifier_flags_uncited_bold_claims():
    """Verify quantitative or absolute statements without citations are flagged as unsupported claims."""
    sections = {
        "Executive Summary": (
            "The system delivers 99.999% availability and automatically eliminates 45% infrastructure costs without latency penalty."
        )
    }
    evidence_list = [
        {"source_id": "QDR-01", "title": "Base Doc", "content": "Base guidelines."}
    ]

    result = verify_draft_faithfulness(sections, evidence_list)

    assert result["hallucination_detected"] is True
    assert len(result["unsupported_claims"]) > 0
    assert result["faithfulness_score"] < 1.0


def test_extract_source_ids_handles_various_formats():
    """Verify source ID extractor parses simple and decorated citations."""
    text = (
        "According to [QDR-01: Architectural Guidelines] and [EXT-05] along with "
        "[CSV-01: Empirical Benchmarks] and [COST-01]."
    )
    sids = FaithfulnessVerifier.extract_source_ids(text)
    assert sids == ["QDR-01", "EXT-05", "CSV-01", "COST-01"]
