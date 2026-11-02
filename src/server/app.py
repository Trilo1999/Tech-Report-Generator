"""FastAPI application for AI Research & Report Generation Agent."""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.graph.builder import create_research_graph
from src.graph.checkpoints import get_checkpointer, get_thread_state, resume_workflow

# Setup FastAPI App
app = FastAPI(
    title="AI Research & Report Generation Agent",
    description="Agentic technical research, deterministic data analysis, human-in-the-loop review, and publication export.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic Request Models
class ResearchStartRequest(BaseModel):
    topic: str = Field(..., description="Broad technical research topic or decision scope")
    thread_id: Optional[str] = Field(None, description="Optional custom thread ID for persistence")


class HumanReviewRequest(BaseModel):
    decision: Literal["approved", "revise", "rejected"] = Field(..., description="Human review decision")
    feedback_notes: Optional[str] = Field("", description="Reviewer feedback or revision instructions")
    target_sections: Optional[List[str]] = Field(default_factory=list, description="Sections to surgically modify")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the single-page Human-in-the-Loop review dashboard."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h2>Review dashboard static template not found</h2>", status_code=404)
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.post("/api/research/start")
async def start_research(request: ResearchStartRequest) -> Dict[str, Any]:
    """
    Initialize a new research workflow thread.
    Executes through planning, evidence gathering, calculation, and drafting,
    then pauses at the human review interrupt checkpoint.
    """
    thread_id = request.thread_id or f"research_{uuid.uuid4().hex[:12]}"
    checkpointer = get_checkpointer()
    graph = create_research_graph(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    initial_input = {"topic": request.topic}

    try:
        state = graph.invoke(initial_input, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

    snapshot = get_thread_state(thread_id, checkpointer=checkpointer)

    return {
        "thread_id": thread_id,
        "status": state.get("status", "drafted"),
        "subquestions": state.get("subquestions", []),
        "evidence_count": len(state.get("evidence", [])),
        "draft_report": state.get("draft_report"),
        "unsupported_claims": state.get("unsupported_claims", []),
        "is_pending_review": "human_review" in (snapshot.get("next", []) if snapshot else []),
    }


@app.get("/api/research/status/{thread_id}")
async def get_status(thread_id: str) -> Dict[str, Any]:
    """Retrieve full state snapshot and current pending actions for a research thread."""
    snapshot = get_thread_state(thread_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Research thread '{thread_id}' not found.")

    values = snapshot["values"]
    return {
        "thread_id": thread_id,
        "status": values.get("status"),
        "topic": values.get("topic"),
        "subquestions": values.get("subquestions", []),
        "evidence": values.get("evidence", []),
        "calculations": values.get("calculations", {}),
        "draft_report": values.get("draft_report"),
        "unsupported_claims": values.get("unsupported_claims", []),
        "final_report_path": values.get("final_report_path"),
        "next": snapshot["next"],
        "is_pending_review": "human_review" in snapshot["next"],
    }


@app.post("/api/research/review/{thread_id}")
async def submit_review(thread_id: str, request: HumanReviewRequest) -> Dict[str, Any]:
    """
    Deliver human reviewer verdict to resume the paused thread.
    - 'approved': Completes report synthesis and exports PDF.
    - 'revise': Surgically rewrites target sections and pauses again.
    - 'rejected': Terminates workflow.
    """
    snapshot = get_thread_state(thread_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Research thread '{thread_id}' not found.")

    if "human_review" not in snapshot.get("next", []):
        raise HTTPException(status_code=400, detail="Thread is not currently awaiting review.")

    review_payload = {
        "decision": request.decision,
        "feedback_notes": request.feedback_notes or "",
        "target_sections": request.target_sections or [],
    }

    try:
        final_state = resume_workflow(thread_id, review_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resumption failed: {str(e)}")

    updated_snapshot = get_thread_state(thread_id)

    return {
        "thread_id": thread_id,
        "status": final_state.get("status"),
        "draft_report": final_state.get("draft_report"),
        "final_report_path": final_state.get("final_report_path"),
        "is_pending_review": "human_review" in (updated_snapshot.get("next", []) if updated_snapshot else []),
    }


@app.get("/api/research/download/{thread_id}")
async def download_report(thread_id: str):
    """Download the final exported PDF report for an approved research thread."""
    snapshot = get_thread_state(thread_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found.")

    report_path_str = snapshot["values"].get("final_report_path")
    if not report_path_str:
        raise HTTPException(status_code=400, detail="No exported report found. The proposal must be approved first.")

    report_path = Path(report_path_str)
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Exported report file not found on disk.")

    return FileResponse(
        path=str(report_path),
        filename=report_path.name,
        media_type="application/pdf",
    )
