"""
Integration and persistence tests for Human-in-the-Loop checkpointing and resumption.
"""

from src.graph.builder import create_research_graph
from src.graph.checkpoints import get_checkpointer, get_thread_state, resume_workflow


def test_checkpointer_initialization():
    """Verify checkpointer creates an isolated in-memory or file-backed database."""
    saver = get_checkpointer(":memory:")
    assert saver is not None


def test_hitl_pause_and_state_inspection():
    """Verify workflow pauses at human_review interrupt and can be inspected via thread_id."""
    checkpointer = get_checkpointer(":memory:")
    graph = create_research_graph(checkpointer=checkpointer)

    thread_id = "thread_hitl_inspect_1"
    config = {"configurable": {"thread_id": thread_id}}

    initial_input = {"topic": "PostgreSQL vs MongoDB Architecture Evaluation"}
    state_after_pause = graph.invoke(initial_input, config=config)

    assert state_after_pause is not None
    assert state_after_pause["status"] == "drafted"
    assert state_after_pause.get("draft_report") is not None

    # Inspect snapshot via get_thread_state helper
    snapshot = get_thread_state(thread_id, checkpointer=checkpointer)
    assert snapshot is not None
    assert "human_review" in snapshot["next"]
    assert snapshot["values"]["topic"] == "PostgreSQL vs MongoDB Architecture Evaluation"


def test_hitl_resume_approved_path():
    """Verify paused thread resumes with approved decision and exports report."""
    checkpointer = get_checkpointer(":memory:")
    graph = create_research_graph(checkpointer=checkpointer)

    thread_id = "thread_hitl_approve_1"
    config = {"configurable": {"thread_id": thread_id}}

    initial_input = {"topic": "Enterprise Database Decision"}
    graph.invoke(initial_input, config=config)

    # Resume with approval
    review_payload = {
        "decision": "approved",
        "feedback_notes": "Security guidelines verified.",
        "target_sections": [],
    }
    final_state = resume_workflow(thread_id, review_payload, checkpointer=checkpointer)

    assert final_state["status"] == "completed"
    assert final_state.get("final_report_path") is not None
    assert final_state["final_report_path"].endswith(".pdf")


def test_hitl_resume_revision_cycle():
    """Verify paused thread can be revised, loops back to human_review, and completes on approval."""
    checkpointer = get_checkpointer(":memory:")
    graph = create_research_graph(checkpointer=checkpointer)

    thread_id = "thread_hitl_revision_1"
    config = {"configurable": {"thread_id": thread_id}}

    initial_input = {"topic": "Database Architecture Revision"}
    graph.invoke(initial_input, config=config)

    # 1. Resume with revision request
    revision_payload = {
        "decision": "revise",
        "feedback_notes": "Include 36-month reserved instance pricing.",
        "target_sections": ["TCO & Cloud Cost Projection"],
    }
    revised_state = resume_workflow(thread_id, revision_payload, checkpointer=checkpointer)

    # Should have updated section and paused AGAIN at human_review
    assert revised_state["status"] == "drafted" or revised_state["status"] == "revised"
    sections = revised_state["draft_report"]["sections"]
    assert "36-month" in sections["TCO & Cloud Cost Projection"]

    snapshot = get_thread_state(thread_id, checkpointer=checkpointer)
    assert "human_review" in snapshot["next"]

    # 2. Second resume with approval
    approval_payload = {
        "decision": "approved",
        "feedback_notes": "Revision verified.",
        "target_sections": [],
    }
    final_state = resume_workflow(thread_id, approval_payload, checkpointer=checkpointer)

    assert final_state["status"] == "completed"
    assert final_state.get("final_report_path") is not None


def test_hitl_resume_rejected_path():
    """Verify paused thread terminates when reviewer rejects."""
    checkpointer = get_checkpointer(":memory:")
    graph = create_research_graph(checkpointer=checkpointer)

    thread_id = "thread_hitl_reject_1"
    config = {"configurable": {"thread_id": thread_id}}

    initial_input = {"topic": "Database Architecture"}
    graph.invoke(initial_input, config=config)

    reject_payload = {
        "decision": "rejected",
        "feedback_notes": "Not approved.",
        "target_sections": [],
    }
    final_state = resume_workflow(thread_id, reject_payload, checkpointer=checkpointer)

    assert final_state["status"] == "rejected"
    assert final_state.get("final_report_path") is None
