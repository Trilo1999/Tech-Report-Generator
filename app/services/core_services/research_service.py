"""Research workflow execution and task lifecycle service implementing OOP patterns."""

import asyncio
from typing import Any, Dict, List, Literal, Optional
import uuid

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.agents.graph.checkpoints import get_thread_state, resume_workflow
from app.services.iam_services.research_auth import User
from app.services.core_services.task_service import TaskManager, task_manager


class ResearchStartRequest(BaseModel):
    topic: str = Field(..., description="Broad technical research topic or decision scope")
    thread_id: Optional[str] = Field(None, description="Optional custom thread ID for persistence")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously (useful for tests and automation)")


class HumanReviewRequest(BaseModel):
    decision: Literal["approved", "revise", "rejected"] = Field(..., description="Human review decision")
    feedback_notes: Optional[str] = Field("", description="Reviewer feedback or revision instructions")
    target_sections: Optional[List[str]] = Field(default_factory=list, description="Sections to surgically modify")
    sync: Optional[bool] = Field(False, description="Whether to block synchronously until review cycle completes")


class ResearchService:
    """Service class managing autonomous research workflows, human review checkpoints, and task state."""

    def __init__(self, manager: TaskManager = task_manager):
        self.manager = manager

    def list_tasks(self, current_user: User) -> List[Dict[str, Any]]:
        """Retrieve research tasks specific to the currently logged in user (or all if admin)."""
        is_admin = current_user.role == "admin"
        return self.manager.list_tasks(user_id=current_user.id, is_admin=is_admin)

    def delete_task(self, thread_id: str, current_user: User) -> Dict[str, Any]:
        """Delete a research task from user history."""
        is_admin = current_user.role == "admin"
        deleted = self.manager.delete_task(thread_id=thread_id, user_id=current_user.id, is_admin=is_admin)
        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found or unauthorized to delete.")
        return {"status": "deleted", "thread_id": thread_id}

    async def start_research(self, request: ResearchStartRequest, current_user: User) -> Dict[str, Any]:
        """Initialize a new research workflow thread as synchronous or background task."""
        thread_id = request.thread_id or f"research_{uuid.uuid4().hex[:12]}"
        self.manager.create_task(
            thread_id=thread_id,
            topic=request.topic,
            user_id=current_user.id,
            user_name=current_user.name,
        )

        if request.sync:
            await self.manager.execute_research_background(thread_id, request.topic)
            task = self.manager.get_task(thread_id)
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

        # Asynchronous non-blocking background task
        asyncio.create_task(self.manager.execute_research_background(thread_id, request.topic))
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

    def get_task_status(self, thread_id: str) -> Dict[str, Any]:
        """Retrieve real-time background task progress, state snapshot, and pending review actions."""
        task = self.manager.get_task(thread_id)
        try:
            snapshot = get_thread_state(thread_id)
        except Exception as exc:
            snapshot = None
            if task:
                task.error = str(exc)
                task.status = "failed"
                task.is_running = False
                self.manager.save_task(task)

        if not snapshot and not task:
            raise HTTPException(status_code=404, detail=f"Research thread '{thread_id}' not found.")

        if not snapshot and task:
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
            self.manager.save_task(task)

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

    async def submit_human_review(
        self, thread_id: str, request: HumanReviewRequest, current_user: User
    ) -> Dict[str, Any]:
        """Deliver human reviewer verdict to resume the paused thread."""
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

        asyncio.create_task(self.manager.execute_review_background(thread_id, review_payload))
        return {
            "thread_id": thread_id,
            "task_id": thread_id,
            "status": "processing",
            "is_running": True,
            "is_pending_review": False,
            "message": f"Review verdict '{request.decision}' dispatched in background. Poll status at /api/research/status/{thread_id}",
            "status_url": f"/api/research/status/{thread_id}",
        }


# Singleton service instance
default_research_service = ResearchService()

# Backwards compatibility function aliases
list_research_tasks = default_research_service.list_tasks
delete_research_task = default_research_service.delete_task
start_research = default_research_service.start_research
get_task_status = default_research_service.get_task_status
submit_human_review = default_research_service.submit_human_review
