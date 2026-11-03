"""Pydantic and TypedDict schemas for research workflow execution and reporting."""

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from typing_extensions import NotRequired, TypedDict


class ResearchStartRequest(BaseModel):
    """Request payload to initiate a research workflow."""

    topic: str = Field(..., description="Broad technical research topic or decision scope")
    thread_id: Optional[str] = Field(None, description="Optional custom thread ID for persistence")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously (useful for tests and automation)")


class HumanReviewRequest(BaseModel):
    """Request payload for Human-in-the-Loop review verdicts."""

    decision: Literal["approved", "revise", "rejected"] = Field(..., description="Human review decision")
    feedback_notes: Optional[str] = Field("", description="Reviewer feedback or revision instructions")
    target_sections: Optional[List[str]] = Field(default_factory=list, description="Sections to surgically modify")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously until review cycle completes")


class EvidenceItem(TypedDict):
    """Normalized evidence record collected from internal or external sources."""

    source_id: str  # Canonical ID: QDR-01, EXT-01, CSV-01, COST-01
    source_type: Literal["internal_qdrant", "external_mock", "tabular_csv", "cost_calculation"]
    title: str
    content: str
    reliability_score: float
    metadata: Dict[str, Any]


class HumanFeedback(TypedDict):
    """Review verdict and feedback notes delivered by a human operator."""

    decision: Literal["approved", "revise", "rejected"]
    feedback_notes: str
    target_sections: List[str]
    reviewed_at: NotRequired[str]


class ConflictingEvidenceItem(TypedDict):
    """Discrepancy record identified between conflicting data sources."""

    source_a_id: str
    source_b_id: str
    claim_a: str
    claim_b: str
    resolution_strategy: str


class DraftReport(TypedDict):
    """Synthesized technical research report structure."""

    title: str
    sections: Dict[str, str]  # Section name -> Markdown content with citations
    cited_sources: List[str]  # List of cited source_ids
    unsupported_claims: NotRequired[List[str]]
    created_at: NotRequired[str]


class WorkerTask(TypedDict):
    """Sub-task dispatched to a specialized worker subagent."""

    id: str
    worker: Literal["internal_research_worker", "external_research_worker", "analytics_worker"]
    description: str
    target_dimension: str
    query: str


def merge_calculations(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reducer to merge calculation dictionaries across parallel orchestrator workers."""
    merged = dict(a) if a else {}
    if b and isinstance(b, dict):
        merged.update(b)
    return merged


class ResearchState(TypedDict):
    """Complete LangGraph workflow state accumulator."""

    topic: str
    subquestions: List[str]
    evidence: Annotated[List[EvidenceItem], operator.add]  # Monoid accumulator across loops
    calculations: Annotated[Dict[str, Any], merge_calculations]  # Reducer merged dictionary
    iteration_count: int
    is_sufficient: bool
    missing_gaps: List[str]
    conflicting_evidence: List[ConflictingEvidenceItem]
    draft_report: Optional[DraftReport]
    unsupported_claims: List[str]
    human_feedback: Optional[HumanFeedback]
    final_report_path: Optional[str]
    status: Literal[
        "init",
        "planning",
        "gathering",
        "calculating",
        "evaluating",
        "drafted",
        "review_pending",
        "revised",
        "approved",
        "rejected",
        "completed",
        "supervising",
        "orchestrating",
    ]
    # Supervisor multi-agent orchestration & monitoring fields
    next_agent: NotRequired[Optional[str]]
    supervisor_notes: NotRequired[Optional[str]]
    subagent_history: NotRequired[Annotated[List[Dict[str, Any]], operator.add]]
    # Orchestrator-Worker pattern fields
    worker_tasks: NotRequired[List[WorkerTask]]
    orchestrator_plan: NotRequired[Optional[str]]
    current_task: NotRequired[Optional[Dict[str, Any]]]
