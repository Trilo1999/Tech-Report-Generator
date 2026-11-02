"""
Unit tests for LangGraph Wiring, Conditional Routers, and Graph Compilation.
"""

from unittest.mock import patch

from langgraph.graph import END

from src.graph.builder import build_research_graph, create_research_graph
from src.graph.edges import route_review, route_sufficiency
from src.state import ResearchState


def test_route_sufficiency_logic():
    """Verify route_sufficiency branches correctly based on sufficiency and iteration limits."""
    # Case 1: Insufficient and within iteration limit -> Loop back to gather_evidence
    state_loop: ResearchState = {
        "topic": "Topic",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": ["Gap 1"],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }
    assert route_sufficiency(state_loop) == "gather_evidence"

    # Case 2: Sufficient -> Proceed to draft_report
    state_sufficient: ResearchState = {
        "topic": "Topic",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }
    assert route_sufficiency(state_sufficient) == "draft_report"

    # Case 3: Insufficient but hit max iteration limit (2) -> Force break to draft_report
    state_max_iter: ResearchState = {
        "topic": "Topic",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 2,
        "is_sufficient": False,
        "missing_gaps": ["Remaining gap"],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }
    assert route_sufficiency(state_max_iter) == "draft_report"


def test_route_review_logic():
    """Verify route_review branches correctly based on reviewer decision."""
    base_state: ResearchState = {
        "topic": "Topic",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "review_pending",
    }

    # Approved -> export_report
    state_approved = dict(base_state)
    state_approved["human_feedback"] = {
        "decision": "approved",
        "feedback_notes": "All criteria met.",
        "target_sections": [],
    }
    assert route_review(state_approved) == "export_report"

    # Revise -> revise_sections
    state_revise = dict(base_state)
    state_revise["human_feedback"] = {
        "decision": "revise",
        "feedback_notes": "Expand benchmark charts.",
        "target_sections": ["Performance & Benchmark Analysis"],
    }
    assert route_review(state_revise) == "revise_sections"

    # Rejected -> END
    state_rejected = dict(base_state)
    state_rejected["human_feedback"] = {
        "decision": "rejected",
        "feedback_notes": "Proposal cancelled.",
        "target_sections": [],
    }
    assert route_review(state_rejected) == END


def test_graph_compilation_and_nodes():
    """Verify that build_research_graph and create_research_graph construct all 8 nodes."""
    workflow = build_research_graph()
    assert workflow is not None

    # Check that all 8 core nodes exist
    expected_nodes = {
        "plan_research",
        "gather_evidence",
        "execute_calculations",
        "evaluate_evidence",
        "draft_report",
        "human_review",
        "revise_sections",
        "export_report",
    }
    actual_nodes = set(workflow.nodes.keys())
    assert expected_nodes.issubset(actual_nodes), f"Missing nodes: {expected_nodes - actual_nodes}"

    # Verify graph compiles successfully
    compiled = create_research_graph()
    assert compiled is not None


def test_graph_full_execution_approved_path():
    """Verify end-to-end graph execution under an approved review verdict."""
    compiled = create_research_graph()

    mock_review_feedback = {
        "decision": "approved",
        "feedback_notes": "Approved by technical reviewer.",
        "target_sections": [],
    }

    initial_input = {
        "topic": "PostgreSQL vs MongoDB High-Concurrency Evaluation",
    }

    with patch("src.graph.nodes.interrupt", return_value=mock_review_feedback):
        final_state = compiled.invoke(initial_input)

        assert final_state is not None
        assert final_state["status"] == "completed"
        assert len(final_state["subquestions"]) >= 3
        assert len(final_state["evidence"]) >= 3
        assert final_state["draft_report"] is not None
        assert final_state["final_report_path"] is not None
        assert final_state["final_report_path"].endswith(".pdf")


def test_graph_full_execution_revision_then_approval():
    """Verify graph supports the human revision loop and subsequent approval."""
    compiled = create_research_graph()

    # First interrupt returns 'revise', second returns 'approved'
    review_responses = [
        {
            "decision": "revise",
            "feedback_notes": "Revise the TCO section with 36-month projections.",
            "target_sections": ["TCO & Cloud Cost Projection"],
        },
        {
            "decision": "approved",
            "feedback_notes": "Revision verified and approved.",
            "target_sections": [],
        },
    ]

    initial_input = {
        "topic": "PostgreSQL vs MongoDB Architecture Evaluation",
    }

    with patch("src.graph.nodes.interrupt", side_effect=review_responses):
        final_state = compiled.invoke(initial_input)

        assert final_state is not None
        assert final_state["status"] == "completed"
        sections = final_state["draft_report"]["sections"]
        assert "36-month" in sections["TCO & Cloud Cost Projection"]
        assert final_state["final_report_path"] is not None


def test_graph_full_execution_rejected_path():
    """Verify graph terminates immediately without export when reviewer rejects."""
    compiled = create_research_graph()

    mock_reject_feedback = {
        "decision": "rejected",
        "feedback_notes": "Out of scope for current quarter.",
        "target_sections": [],
    }

    initial_input = {
        "topic": "Experimental In-Memory Datastore Evaluation",
    }

    with patch("src.graph.nodes.interrupt", return_value=mock_reject_feedback):
        final_state = compiled.invoke(initial_input)

        assert final_state is not None
        assert final_state["status"] == "rejected"
        assert final_state.get("final_report_path") is None
