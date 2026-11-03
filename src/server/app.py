"""FastAPI application for AI Research & Report Generation Agent."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import uuid

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from src.graph.checkpoints import get_thread_state, resume_workflow
from src.server.auth import (
    DEMO_ACCOUNTS,
    DemoUserPublic,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    User,
    bearer_scheme,
    create_access_token,
    create_user,
    decode_access_token,
    get_current_user,
    get_user_by_email,
    get_user_by_id,
    init_auth_db,
    require_roles,
    verify_password,
)
from src.server.tasks import task_manager

# Initialize authentication persistence and demo credentials
init_auth_db()

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


# Pydantic Request Models
class ResearchStartRequest(BaseModel):
    topic: str = Field(..., description="Broad technical research topic or decision scope")
    thread_id: Optional[str] = Field(None, description="Optional custom thread ID for persistence")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously (useful for tests and automation)")


class HumanReviewRequest(BaseModel):
    decision: Literal["approved", "revise", "rejected"] = Field(..., description="Human review decision")
    feedback_notes: Optional[str] = Field("", description="Reviewer feedback or revision instructions")
    target_sections: Optional[List[str]] = Field(default_factory=list, description="Sections to surgically modify")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously until review cycle completes")


@app.get("/")
async def api_root() -> Dict[str, Any]:
    """API Root endpoint for the AI Research & Report Generation Agent backend."""
    return {
        "service": "AI Technical Research & Decision Report Agent API",
        "version": "2.0",
        "status": "healthy",
        "docs_url": "/docs",
        "frontend_url": "http://localhost:3000",
    }


# ──────────────────────────────────────────────
# Authentication Endpoints
# ──────────────────────────────────────────────
@app.post("/api/auth/register", response_model=TokenResponse)
async def register_account(request: RegisterRequest) -> TokenResponse:
    """Register a new user account and return JWT credentials."""
    role = request.role if request.role in ["researcher", "reviewer", "viewer"] else "researcher"
    user = create_user(
        email=request.email,
        name=request.name,
        password=request.password,
        role=role,
    )
    token = create_access_token(user)
    return TokenResponse(access_token=token, user=user)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login_account(request: LoginRequest) -> TokenResponse:
    """Verify email and password credentials, returning JWT access token."""
    user_db = get_user_by_email(request.email)
    if not user_db or not verify_password(request.password, user_db.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = User(
        id=user_db.id,
        email=user_db.email,
        name=user_db.name,
        role=user_db.role,
        created_at=user_db.created_at,
    )
    token = create_access_token(user)
    return TokenResponse(access_token=token, user=user)


@app.get("/api/auth/me", response_model=User)
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> User:
    """Retrieve profile and role information for currently authenticated user."""
    return current_user


@app.get("/api/auth/demo-users", response_model=List[DemoUserPublic])
async def list_demo_accounts() -> List[DemoUserPublic]:
    """Retrieve pre-configured demo credentials for instantaneous UI role testing."""
    return [DemoUserPublic(**acc) for acc in DEMO_ACCOUNTS]


# ──────────────────────────────────────────────
# Research Workflow Endpoints (Protected by RBAC)
# ──────────────────────────────────────────────
@app.get("/api/research/tasks")
async def list_research_tasks(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Retrieve research tasks specific to the currently logged in user.
    Admin accounts have access to view all active and historical tasks across users.
    """
    is_admin = current_user.role == "admin"
    return task_manager.list_tasks(user_id=current_user.id, is_admin=is_admin)


@app.delete("/api/research/tasks/{thread_id}")
async def delete_research_task(
    thread_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Delete a research task from user history.
    """
    is_admin = current_user.role == "admin"
    deleted = task_manager.delete_task(thread_id=thread_id, user_id=current_user.id, is_admin=is_admin)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized to delete.")
    return {"status": "deleted", "thread_id": thread_id}


@app.post("/api/research/start")
async def start_research(
    request: ResearchStartRequest,
    current_user: User = Depends(require_roles(["admin", "researcher"])),
) -> Dict[str, Any]:
    """
    Initialize a new research workflow thread as an asynchronous background task.
    Restricted to 'admin' and 'researcher' roles.
    """
    thread_id = request.thread_id or f"research_{uuid.uuid4().hex[:12]}"
    task_manager.create_task(
        thread_id=thread_id,
        topic=request.topic,
        user_id=current_user.id,
        user_name=current_user.name,
    )

    if request.sync:
        # Synchronous blocking mode (for tests and automated workflows)
        await task_manager.execute_research_background(thread_id, request.topic)
        task = task_manager.get_task(thread_id)
        if task and task.error:
            raise HTTPException(status_code=500, detail=f"Workflow execution failed: {task.error}")

        snapshot = get_thread_state(thread_id)
        if not snapshot:
            raise HTTPException(status_code=500, detail="Workflow did not generate state snapshot.")
        values = snapshot["values"]
        return {
            "thread_id": thread_id,
            "task_id": thread_id,
            "status": values.get("status", "drafted"),
            "topic": values.get("topic", request.topic),
            "is_running": False,
            "subquestions": values.get("subquestions", []),
            "evidence_count": len(values.get("evidence", [])),
            "draft_report": values.get("draft_report"),
            "unsupported_claims": values.get("unsupported_claims", []),
            "is_pending_review": "human_review" in snapshot.get("next", []),
            "status_url": f"/api/research/status/{thread_id}",
        }

    # Asynchronous non-blocking background task (default)
    asyncio.create_task(task_manager.execute_research_background(thread_id, request.topic))

    return {
        "thread_id": thread_id,
        "task_id": thread_id,
        "topic": request.topic,
        "status": "running",
        "is_running": True,
        "is_pending_review": False,
        "message": f"Autonomous research task initiated in background. Poll status at /api/research/status/{thread_id}",
        "status_url": f"/api/research/status/{thread_id}",
    }


@app.get("/api/research/status/{thread_id}")
async def get_status(
    thread_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve real-time background task progress, state snapshot, and pending review actions.
    Accessible to all authenticated users ('admin', 'researcher', 'reviewer', 'viewer').
    """
    task = task_manager.get_task(thread_id)
    try:
        snapshot = get_thread_state(thread_id)
    except Exception as exc:
        snapshot = None
        if task:
            task.error = str(exc)
            task.status = "failed"
            task.is_running = False
            task_manager.save_task(task)

    if not snapshot and not task:
        raise HTTPException(status_code=404, detail=f"Research thread '{thread_id}' not found.")

    if not snapshot and task:
        # Task is running initial nodes before first checkpoint commit
        return {
            "thread_id": thread_id,
            "task_id": thread_id,
            "status": task.status,
            "topic": task.topic,
            "is_running": task.is_running,
            "subquestions": [],
            "evidence": [],
            "evidence_count": 0,
            "calculations": {},
            "draft_report": None,
            "unsupported_claims": [],
            "final_report_path": None,
            "next": [],
            "is_pending_review": False,
            "error": task.error,
            "message": "Research task is executing in background..." if task.is_running else None,
        }

    values = snapshot["values"]
    is_running = task.is_running if task else False
    status_val = task.status if (task and is_running) else values.get("status", "drafted")
    is_pending = "human_review" in snapshot.get("next", []) and not is_running

    if task and not is_running:
        task.is_pending_review = is_pending
        task.evidence_count = len(values.get("evidence", []))
        task.has_report = bool(values.get("draft_report"))
        task.status = "review_pending" if is_pending else values.get("status", "drafted")
        task_manager.save_task(task)

    return {
        "thread_id": thread_id,
        "task_id": thread_id,
        "status": status_val,
        "topic": values.get("topic", task.topic if task else None),
        "is_running": is_running,
        "subquestions": values.get("subquestions", []),
        "evidence": values.get("evidence", []),
        "evidence_count": len(values.get("evidence", [])),
        "calculations": values.get("calculations", {}),
        "draft_report": values.get("draft_report"),
        "unsupported_claims": values.get("unsupported_claims", []),
        "final_report_path": values.get("final_report_path"),
        "next": snapshot["next"],
        "is_pending_review": is_pending,
        "error": task.error if task else None,
    }


@app.post("/api/research/review/{thread_id}")
async def submit_review(
    thread_id: str,
    request: HumanReviewRequest,
    current_user: User = Depends(require_roles(["admin", "reviewer", "researcher"])),
) -> Dict[str, Any]:
    """
    Deliver human reviewer verdict to resume the paused thread.
    Can execute synchronously or as a background task.
    """
    if request.decision in ["approved", "rejected"] and current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Forbidden: Final '{request.decision}' verdict requires 'admin' or 'reviewer' authority. "
                f"Your role ('{current_user.role}') may only request targeted revisions."
            ),
        )

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

    if request.sync:
        try:
            final_state = resume_workflow(thread_id, review_payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Resumption failed: {str(e)}")

        updated_snapshot = get_thread_state(thread_id)
        return {
            "thread_id": thread_id,
            "task_id": thread_id,
            "status": final_state.get("status"),
            "is_running": False,
            "draft_report": final_state.get("draft_report"),
            "final_report_path": final_state.get("final_report_path"),
            "is_pending_review": "human_review" in (updated_snapshot.get("next", []) if updated_snapshot else []),
        }

    # Asynchronous non-blocking background resumption
    asyncio.create_task(task_manager.execute_review_background(thread_id, review_payload))

    return {
        "thread_id": thread_id,
        "task_id": thread_id,
        "status": "processing",
        "is_running": True,
        "is_pending_review": False,
        "message": f"Review verdict '{request.decision}' dispatched in background. Poll status at /api/research/status/{thread_id}",
        "status_url": f"/api/research/status/{thread_id}",
    }


@app.get("/api/research/download/{thread_id}")
async def download_report(
    thread_id: str,
    format: str = "pdf",
    token: Optional[str] = None,
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
):
    """
    Download the final exported report in PDF or Microsoft Word (.docx) format.
    Accepts Bearer token header or ?token= query parameter.
    Accessible to all authenticated users ('admin', 'researcher', 'reviewer', 'viewer').
    """
    raw_token = auth_credentials.credentials if (auth_credentials and auth_credentials.credentials) else token
    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication token required to download report.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(raw_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")

    snapshot = get_thread_state(thread_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found.")

    report_path_str = snapshot["values"].get("final_report_path")
    if not report_path_str:
        raise HTTPException(status_code=400, detail="No exported report found. The proposal must be approved first.")

    report_path = Path(report_path_str)
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Exported report file not found on disk.")

    target_format = format.lower().strip()
    if target_format in ("docx", "doc", "word"):
        docx_path = report_path.with_suffix(".docx")
        if not docx_path.is_file():
            from src.tools.report_exporter import generate_report

            values = snapshot["values"]
            draft = values.get("draft_report") or {}
            content = {
                "title": draft.get("title", f"Report: {values.get('topic')}"),
                "sections": draft.get("sections", {}),
                "cited_sources": draft.get("cited_sources", []),
                "evidence_items": values.get("evidence", []),
                "unsupported_claims": values.get("unsupported_claims", []),
                "metadata": {"topic": values.get("topic")},
            }
            docx_path = Path(generate_report(content, format="docx"))

        return FileResponse(
            path=str(docx_path),
            filename=docx_path.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    return FileResponse(
        path=str(report_path),
        filename=report_path.name,
        media_type="application/pdf",
    )
