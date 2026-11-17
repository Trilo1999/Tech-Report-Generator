"""Conditional routing logic for the LangGraph Research & Report Generation Agent."""

from typing import Literal

from langgraph.graph import END

from app.agents.graph.state import ResearchState
from app.config.env_config import MAX_RESEARCH_ITERATIONS


def route_sufficiency(
    state: ResearchState,
) -> Literal["gather_evidence", "draft_report"]:
    """
    Evaluate evidence sufficiency and enforce loop boundaries.

    Returns:
        "gather_evidence": If evidence is insufficient and iteration limit not exceeded.
        "draft_report": If evidence is sufficient OR max iterations reached.
    """
    is_sufficient = state.get("is_sufficient", False)
    iteration_count = state.get("iteration_count", 0)

    if not is_sufficient and iteration_count < MAX_RESEARCH_ITERATIONS:
        return "gather_evidence"

    return "draft_report"


def route_reflection(
    state: ResearchState,
) -> Literal["self_correct_report", "human_review"]:
    """
    Route execution following draft_report to determine if automated reflection is needed.

    Returns:
        "self_correct_report": If hallucination/unsupported claims are detected and reflections not exceeded.
        "human_review": If report is sufficiently faithful or max reflections reached.
    """
    hallucination_detected = state.get("hallucination_detected", False)
    unsupported = state.get("unsupported_claims", [])
    reflection_count = state.get("reflection_count", 0)

    if (hallucination_detected or len(unsupported) > 0) and reflection_count < 1:
        return "self_correct_report"

    return "human_review"


def route_review(state: ResearchState) -> str:
    """
    Route execution following human review verdict.

    Returns:
        "export_report": If review was approved.
        "revise_sections": If reviewer requested revisions.
        END ("__end__"): If reviewer rejected the proposal.
    """
    feedback = state.get("human_feedback") or {}
    decision = feedback.get("decision", "approved").lower().strip()

    if decision in ("approved", "approve"):
        return "export_report"
    elif decision in ("revise", "revision"):
        return "revise_sections"
    elif decision in ("rejected", "reject"):
        return END

    return "export_report"
