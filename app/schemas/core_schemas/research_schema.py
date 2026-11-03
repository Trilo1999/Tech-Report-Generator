"""Pydantic and TypedDict schemas for research workflow execution and reporting."""

from typing import Annotated, Any, Dict, List, Literal, Optional
from operator import add
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ResearchStartRequest(BaseModel):
    topic: str = Field(..., description="Broad technical research topic or decision scope")
    thread_id: Optional[str] = Field(None, description="Optional custom thread ID for persistence")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously (useful for tests and automation)")


class HumanReviewRequest(BaseModel):
    decision: Literal["approved", "revise", "rejected"] = Field(..., description="Human review decision")
    feedback_notes: Optional[str] = Field("", description="Reviewer feedback or revision instructions")
    target_sections: Optional[List[str]] = Field(default_factory=list, description="Sections to surgically modify")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously until review cycle completes")


class EvidenceItem(TypedDict):
    source_id: str
    source_type: Literal["internal_qdrant", "external_mock", "tabular_csv", "cost_calculation"]
    title: str
    content: str
    reliability_score: float
    metadata: Dict[str, Any]


class DraftReport(TypedDict):
    title: str
    sections: Dict[str, str]
    cited_sources: List[str]
    created_at: str


class HumanFeedback(TypedDict):
    decision: Literal["approved", "revise", "rejected"]
    feedback_notes: str
    target_sections: List[str]
    reviewed_at: str


class WorkerTask(TypedDict):
    id: str
    worker: Literal["internal_research_worker", "external_research_worker", "analytics_worker"]
    description: str
    target_dimension: str
    query: str


def merge_calculations(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer combining calculation dictionaries safely."""
    merged = dict(existing)
    merged.update(new)
    return merged


class ResearchState(TypedDict):
    topic: str
    subquestions: List[str]
    evidence: Annotated[List[EvidenceItem], add]
    calculations: Annotated[Dict[str, Any], merge_calculations]
    iteration_count: int
    draft_report: Optional[DraftReport]
    human_feedback: Optional[HumanFeedback]
    unsupported_claims: List[str]
    final_report_path: Optional[str]
    status: Literal[
        "init",
        "planning",
        "orchestrating",
        "gathering",
        "analyzing",
        "drafted",
        "reviewed",
        "approved",
        "rejected",
        "published",
    ]
    missing_gaps: List[str]
    next_agent: Optional[str]
    supervisor_notes: Optional[str]
    subagent_history: Annotated[List[Dict[str, Any]], add]
    worker_tasks: Optional[List[WorkerTask]]
    orchestrator_plan: Optional[str]
    current_task: Optional[WorkerTask]
