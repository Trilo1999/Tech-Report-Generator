"""Research workflow execution, monitoring, review, and report routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Security
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

from services.report_service import download_report_file
from services.research_service import (
    HumanReviewRequest,
    ResearchStartRequest,
    delete_research_task,
    get_task_status,
    list_research_tasks,
    start_research,
    submit_human_review,
)
from src.server.auth import (
    User,
    bearer_scheme,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/api/research", tags=["Research Workflow"])


@router.get("/tasks")
async def get_tasks(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieve research tasks specific to the currently logged in user (or all if admin)."""
    return list_research_tasks(current_user)


@router.delete("/tasks/{thread_id}")
async def delete_task(
    thread_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a research task from user history."""
    return delete_research_task(thread_id, current_user)


@router.post("/start")
async def start_research_task(
    request: ResearchStartRequest,
    current_user: User = Depends(require_roles(["admin", "researcher"])),
) -> Dict[str, Any]:
    """Initialize a new research workflow thread as an asynchronous background or synchronous task."""
    return await start_research(request, current_user)


@router.get("/status/{thread_id}")
async def get_status(
    thread_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve real-time background task progress, state snapshot, and pending review actions."""
    return get_task_status(thread_id)


@router.post("/review/{thread_id}")
async def submit_review(
    thread_id: str,
    request: HumanReviewRequest,
    current_user: User = Depends(require_roles(["admin", "reviewer", "researcher"])),
) -> Dict[str, Any]:
    """Deliver human reviewer verdict to resume the paused thread."""
    return await submit_human_review(thread_id, request, current_user)


@router.get("/download/{thread_id}")
async def download_report(
    thread_id: str,
    format: str = "pdf",
    token: Optional[str] = None,
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> FileResponse:
    """Download the final exported report in PDF or Microsoft Word (.docx) format."""
    return download_report_file(
        thread_id=thread_id,
        format=format,
        token=token,
        auth_credentials=auth_credentials,
    )
