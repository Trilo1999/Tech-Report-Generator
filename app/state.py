"""State definition for the LangGraph Research & Report Generation Agent."""

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional
from typing_extensions import NotRequired, TypedDict


class EvidenceItem(TypedDict):
    source_id: str  # Canonical ID: QDR-01, EXT-01, CSV-01, COST-01
    source_type: Literal["internal_qdrant", "external_mock", "tabular_csv", "cost_calculation"]
    title: str
    content: str
    reliability_score: float
    metadata: Dict[str, Any]


class HumanFeedback(TypedDict):
    decision: Literal["approved", "revise", "rejected"]
    feedback_notes: str
    target_sections: List[str]  # Specific sections to modify during revision


class ConflictingEvidenceItem(TypedDict):
    source_a_id: str
    source_b_id: str
    claim_a: str
    claim_b: str
    resolution_strategy: str


class DraftReport(TypedDict):
    title: str
    sections: Dict[str, str]  # Section name -> Markdown content with citations
    cited_sources: List[str]  # List of cited source_ids
    unsupported_claims: List[str]  # Claims made without source backing


class WorkerTask(TypedDict):
    id: str
    worker: str  # "internal_research_worker", "external_research_worker", "analytics_worker"
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
