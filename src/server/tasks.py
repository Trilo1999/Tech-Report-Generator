"""Background task manager for asynchronous agentic research execution.

Allows long-running research and human review workflows to run non-blockingly
in background worker threads while exposing instantaneous task status polling,
task history, and per-user research isolation.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from src.db.postgres import (
    is_postgres_available,
    pg_delete_task,
    pg_get_task,
    pg_list_tasks,
    pg_save_task,
)

logger = logging.getLogger("research_agent.tasks")


class TaskRecord:
    """Tracking record for an asynchronous workflow task."""

    def __init__(
        self,
        task_id: str,
        topic: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        status: str = "running",
        current_step: str = "planning",
        is_running: bool = True,
        is_pending_review: bool = False,
        evidence_count: int = 0,
        has_report: bool = False,
        error: Optional[str] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        now = time.time()
        self.task_id = task_id
        self.thread_id = task_id
        self.topic = topic
        self.user_id = user_id
        self.user_name = user_name
        self.status = status
        self.current_step = current_step
        self.is_running = is_running
        self.is_pending_review = is_pending_review
        self.evidence_count = evidence_count
        self.has_report = has_report
        self.error = error
        self.created_at = created_at if created_at is not None else now
        self.updated_at = updated_at if updated_at is not None else now

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "thread_id": self.thread_id,
            "topic": self.topic,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "status": self.status,
            "current_step": self.current_step,
            "is_running": self.is_running,
            "is_pending_review": self.is_pending_review,
            "evidence_count": self.evidence_count,
            "has_report": self.has_report,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskRecord":
        return cls(
            task_id=data.get("task_id", data.get("thread_id", "")),
            topic=data.get("topic", "Technical Architecture Research"),
            user_id=data.get("user_id"),
            user_name=data.get("user_name"),
            status=data.get("status", "completed"),
            current_step=data.get("current_step", "completed"),
            is_running=data.get("is_running", False),
            is_pending_review=data.get("is_pending_review", False),
            evidence_count=data.get("evidence_count", 0),
            has_report=data.get("has_report", False),
            error=data.get("error"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class TaskManager:
    """Manages background dispatching, monitoring, and state history for research tasks in PostgreSQL."""

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}

    def get_task(self, thread_id: str) -> Optional[TaskRecord]:
        task = self._tasks.get(thread_id)
        if task:
            return task
        if is_postgres_available():
            pg_row = pg_get_task(thread_id)
            if pg_row:
                rec = TaskRecord.from_dict(pg_row)
                self._tasks[thread_id] = rec
                return rec
        return None

    def create_task(
        self,
        thread_id: str,
        topic: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> TaskRecord:
        task = TaskRecord(
            task_id=thread_id,
            topic=topic,
            user_id=user_id,
            user_name=user_name,
            status="running",
            is_running=True,
        )
        self._tasks[thread_id] = task
        if is_postgres_available():
            pg_save_task(task.to_dict())
        return task

    def save_task(self, task: TaskRecord) -> None:
        """Persist task record to PostgreSQL."""
        self._tasks[task.thread_id] = task
        if is_postgres_available():
            pg_save_task(task.to_dict())

    def list_tasks(
        self,
        user_id: Optional[str] = None,
        is_admin: bool = False,
    ) -> List[Dict[str, Any]]:
        """List tasks matching user identity directly from PostgreSQL."""
        tasks_map: Dict[str, Dict[str, Any]] = {}

        # 1. Read from PostgreSQL
        if is_postgres_available():
            for row in pg_list_tasks(user_id=user_id, is_admin=is_admin):
                tid = row["thread_id"]
                tasks_map[tid] = row

        # 2. Overlay live in-memory tasks
        for task in self._tasks.values():
            if is_admin or not user_id or task.user_id == user_id:
                tasks_map[task.thread_id] = task.to_dict()

        results = list(tasks_map.values())
        results.sort(key=lambda t: t.get("created_at", 0), reverse=True)
        return results

    def delete_task(
        self,
        thread_id: str,
        user_id: Optional[str] = None,
        is_admin: bool = False,
    ) -> bool:
        """Delete task from PostgreSQL and memory."""
        deleted_pg = False
        if is_postgres_available():
            deleted_pg = pg_delete_task(thread_id=thread_id, user_id=user_id, is_admin=is_admin)

        task = self._tasks.get(thread_id)
        if not task:
            return deleted_pg

        if not is_admin and user_id and task.user_id != user_id:
            return False

        del self._tasks[thread_id]
        return True

    async def execute_research_background(self, thread_id: str, topic: str) -> None:
        """Execute research graph in a background thread."""
        task = self._tasks.get(thread_id)
        from src.graph.builder import create_research_graph
        from src.graph.checkpoints import get_checkpointer, get_thread_state

        checkpointer = get_checkpointer()
        graph = create_research_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        initial_input = {"topic": topic}

        try:
            # Run graph execution in worker thread to prevent blocking async event loop
            await asyncio.to_thread(graph.invoke, initial_input, config)
            snapshot = get_thread_state(thread_id, checkpointer=checkpointer)

            if task:
                task.is_running = False
                task.updated_at = time.time()
                if snapshot:
                    values = snapshot.get("values", {})
                    is_pending = "human_review" in snapshot.get("next", [])
                    task.is_pending_review = is_pending
                    task.evidence_count = len(values.get("evidence", []))
                    task.has_report = bool(values.get("draft_report"))
                    task.status = "review_pending" if is_pending else values.get("status", "drafted")
                    task.current_step = "human_review" if is_pending else "drafted"
                else:
                    task.status = "drafted"
                    task.current_step = "drafted"
                if is_postgres_available():
                    pg_save_task(task.to_dict())
        except Exception as exc:
            logger.exception("Background research failed for thread %s", thread_id)
            if task:
                task.is_running = False
                task.status = "failed"
                task.error = str(exc)
                task.updated_at = time.time()
                if is_postgres_available():
                    pg_save_task(task.to_dict())

    async def execute_review_background(self, thread_id: str, review_payload: Dict[str, Any]) -> None:
        """Execute review resumption in a background thread."""
        task = self._tasks.get(thread_id)
        if task:
            task.is_running = True
            task.status = "review_resuming"
            task.updated_at = time.time()
            if is_postgres_available():
                pg_save_task(task.to_dict())

        try:
            from src.graph.checkpoints import get_thread_state, resume_workflow

            await asyncio.to_thread(resume_workflow, thread_id, review_payload)
            snapshot = get_thread_state(thread_id)

            if task:
                task.is_running = False
                task.updated_at = time.time()
                if snapshot:
                    values = snapshot.get("values", {})
                    is_pending = "human_review" in snapshot.get("next", [])
                    task.is_pending_review = is_pending
                    task.evidence_count = len(values.get("evidence", []))
                    task.has_report = bool(values.get("draft_report"))
                    task.status = "review_pending" if is_pending else values.get("status", "completed")
                    task.current_step = "human_review" if is_pending else "completed"
                else:
                    task.status = "completed"
                    task.current_step = "completed"
                if is_postgres_available():
                    pg_save_task(task.to_dict())
        except Exception as exc:
            logger.exception("Background review resumption failed for thread %s", thread_id)
            if task:
                task.is_running = False
                task.status = "failed"
                task.error = str(exc)
                task.updated_at = time.time()
                if is_postgres_available():
                    pg_save_task(task.to_dict())


# Singleton instance
task_manager = TaskManager()
