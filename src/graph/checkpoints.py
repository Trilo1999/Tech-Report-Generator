"""Checkpointer setup and persistence management for Human-in-the-Loop workflows.

Uses PostgreSQL via PostgresSaver for all production graph runs.
"""

import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from psycopg_pool import ConnectionPool

from src.config import POSTGRES_URL
from src.graph.builder import create_research_graph

logger = logging.getLogger("research_agent.checkpoints")

_GLOBAL_PG_POOL: Optional[ConnectionPool] = None
_GLOBAL_PG_CHECKPOINTER: Optional[BaseCheckpointSaver] = None


def reset_checkpointer() -> None:
    """Reset cached checkpointer connections."""
    global _GLOBAL_PG_POOL, _GLOBAL_PG_CHECKPOINTER

    if _GLOBAL_PG_POOL:
        try:
            _GLOBAL_PG_POOL.close()
        except Exception:
            pass
    _GLOBAL_PG_POOL = None
    _GLOBAL_PG_CHECKPOINTER = None


def get_checkpointer(db_path: Optional[str | Path] = None) -> BaseCheckpointSaver:
    """
    Get or create a checkpointer instance.
    Directly uses PostgreSQL (PostgresSaver) for all production graph runs.
    When db_path is explicitly provided (e.g. unit tests with ':memory:'), SqliteSaver is used.
    """
    global _GLOBAL_PG_POOL, _GLOBAL_PG_CHECKPOINTER

    # Explicit local/isolated path (used in unit tests)
    if db_path is not None:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        return SqliteSaver(conn)

    # Production checkpointer: PostgreSQL
    if _GLOBAL_PG_CHECKPOINTER is None:
        from langgraph.checkpoint.postgres import PostgresSaver

        _GLOBAL_PG_POOL = ConnectionPool(
            conninfo=POSTGRES_URL,
            max_size=10,
            open=True,
            kwargs={"autocommit": True},
        )
        cp = PostgresSaver(_GLOBAL_PG_POOL)
        cp.setup()
        _GLOBAL_PG_CHECKPOINTER = cp
        logger.info("LangGraph checkpointer initialized with PostgreSQL on %s", POSTGRES_URL)

    return _GLOBAL_PG_CHECKPOINTER


def get_thread_state(
    thread_id: str,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve current snapshot and pending next nodes for a given thread ID."""
    try:
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
    except Exception as exc:
        logger.warning("get_thread_state failed for thread %s: %s", thread_id, exc)
        return None


def resume_workflow(
    thread_id: str,
    review_payload: Dict[str, Any],
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> Dict[str, Any]:
    """
    Resume an interrupted workflow thread by providing the reviewer's decision payload.
    """
    cp = checkpointer or get_checkpointer()
    graph = create_research_graph(checkpointer=cp)
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(Command(resume=review_payload), config=config)
