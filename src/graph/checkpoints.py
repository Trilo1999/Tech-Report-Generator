"""Checkpointer setup and persistence management for Human-in-the-Loop workflows."""

from pathlib import Path
import sqlite3
from typing import Any, Dict, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src.config import CHECKPOINT_DB_PATH
from src.graph.builder import create_research_graph

_GLOBAL_SQLITE_CONN: Optional[sqlite3.Connection] = None
_GLOBAL_CHECKPOINTER: Optional[SqliteSaver] = None


def get_checkpointer(db_path: Optional[str | Path] = None) -> SqliteSaver:
    """
    Get or create a singleton SqliteSaver checkpointer.
    Persists workflow snapshots to SQLite (default: data/checkpoints.db or :memory:).
    """
    global _GLOBAL_SQLITE_CONN, _GLOBAL_CHECKPOINTER

    if db_path is not None:
        # Create isolated instance (used for unit tests with ':memory:')
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        return SqliteSaver(conn)

    if _GLOBAL_CHECKPOINTER is None:
        target_path = Path(CHECKPOINT_DB_PATH)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _GLOBAL_SQLITE_CONN = sqlite3.connect(str(target_path), check_same_thread=False)
        _GLOBAL_CHECKPOINTER = SqliteSaver(_GLOBAL_SQLITE_CONN)

    return _GLOBAL_CHECKPOINTER


def get_thread_state(thread_id: str, checkpointer: Optional[SqliteSaver] = None) -> Optional[Dict[str, Any]]:
    """Retrieve current snapshot and pending next nodes for a given thread ID."""
    cp = checkpointer or get_checkpointer()
    graph = create_research_graph(checkpointer=cp)
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = graph.get_state(config)
    if state_snapshot and state_snapshot.values:
        return {
            "values": state_snapshot.values,
            "next": list(state_snapshot.next),
            "created_at": getattr(state_snapshot, "created_at", None),
        }
    return None


def resume_workflow(
    thread_id: str,
    review_payload: Dict[str, Any],
    checkpointer: Optional[SqliteSaver] = None,
) -> Dict[str, Any]:
    """
    Resume an interrupted workflow thread by providing the reviewer's decision payload.
    """
    cp = checkpointer or get_checkpointer()
    graph = create_research_graph(checkpointer=cp)
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(Command(resume=review_payload), config=config)
