"""Unit tests for automated self-correction and reflection loop."""

from app.agents.graph.edges import route_reflection
from app.agents.graph.nodes import self_correct_report


def test_route_reflection_routes_to_self_correction_when_unsupported():
    """Verify route_reflection routes to self_correct_report when unsupported claims exist."""
    state = {
        "hallucination_detected": True,
        "unsupported_claims": ["MongoDB query optimizer eliminates all latency."],
        "reflection_count": 0,
    }
    next_node = route_reflection(state)
    assert next_node == "self_correct_report"


def test_route_reflection_routes_to_human_review_when_clean():
    """Verify route_reflection routes directly to human_review when no hallucinations detected."""
    state = {
        "hallucination_detected": False,
        "unsupported_claims": [],
        "reflection_count": 0,
    }
    next_node = route_reflection(state)
    assert next_node == "human_review"


def test_route_reflection_enforces_max_reflection_limit():
    """Verify route_reflection does not loop indefinitely when reflection limit is reached."""
    state = {
        "hallucination_detected": True,
        "unsupported_claims": ["Unverified claim."],
        "reflection_count": 1,
    }
    next_node = route_reflection(state)
    assert next_node == "human_review"


def test_self_correct_report_refines_unsupported_assertions():
    """Verify self_correct_report softens unverified claims and updates state."""
    initial_draft = {
        "title": "Database Architecture Report",
        "sections": {
            "Executive Summary": (
                "PostgreSQL scales reliably [QDR-01]. "
                "System provides zero cross-shard latency without penalty."
            ),
        },
        "cited_sources": ["QDR-01"],
        "unsupported_claims": [
            "System provides zero cross-shard latency without penalty."
        ],
    }
    evidence_list = [
        {
            "source_id": "QDR-01",
            "title": "Guidelines",
            "content": "PostgreSQL enterprise architectural standards.",
        }
    ]
    state = {
        "draft_report": initial_draft,
        "evidence": evidence_list,
        "unsupported_claims": initial_draft["unsupported_claims"],
        "reflection_count": 0,
        "reflection_notes": [],
    }

    result = self_correct_report(state)

    assert result["status"] == "drafted"
    assert result["reflection_count"] == 1
    assert "draft_report" in result
    corrected_sections = result["draft_report"]["sections"]
    assert (
        "Subject to workload-specific validation"
        in corrected_sections["Executive Summary"]
    )
