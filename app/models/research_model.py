"""Domain models for research workflow tasks, precedent memories, and access control."""

import time
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RoleType = Literal["admin", "researcher", "reviewer", "viewer"]


class ResearchUserModel(BaseModel):
    """User domain model for research system access and RBAC authorization."""

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    name: str
    role: RoleType
    created_at: float


class TaskModel(BaseModel):
    """Domain model representing a persistent research workflow execution thread."""

    model_config = ConfigDict(frozen=False)

    task_id: str
    thread_id: str
    topic: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    status: str = "running"
    current_step: str = "planning"
    is_running: bool = True
    is_pending_review: bool = False
    evidence_count: int = 0
    has_report: bool = False
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert domain model instance to standard dictionary."""
        return self.model_dump()


class ResearchMemoryModel(BaseModel):
    """Domain model for cross-session precedent knowledge recall."""

    model_config = ConfigDict(frozen=True)

    id: str
    topic: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
