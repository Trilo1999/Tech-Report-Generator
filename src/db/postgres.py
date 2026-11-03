"""PostgreSQL database service for AI Research & Report Generation Agent.

Manages connections, schema initialization, users, research tasks,
and integrates with LangGraph PostgresSaver checkpointer.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import uuid

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from src.config import POSTGRES_URL

logger = logging.getLogger("research_agent.db")

_POSTGRES_AVAILABLE: Optional[bool] = None


def get_postgres_conn() -> psycopg.Connection:
    """Establish and return a new PostgreSQL connection with dictionary row mapping."""
    return psycopg.connect(POSTGRES_URL, row_factory=dict_row)


def is_postgres_available() -> bool:
    """Check if PostgreSQL container/server is reachable."""
    global _POSTGRES_AVAILABLE
    if _POSTGRES_AVAILABLE is not None:
        return _POSTGRES_AVAILABLE
    try:
        with psycopg.connect(POSTGRES_URL, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        _POSTGRES_AVAILABLE = True
        return True
    except Exception as exc:
        logger.info("PostgreSQL is not reachable (%s); falling back to local storage.", exc)
        _POSTGRES_AVAILABLE = False
        return False


def init_postgres_schema(demo_accounts: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    Initialize PostgreSQL relational schema:
    1. users table & indexes
    2. research_tasks table & indexes
    3. LangGraph checkpoints tables via PostgresSaver
    4. Seed demo users if empty
    """
    if not is_postgres_available():
        return False

    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                # 1. Users Table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(64) PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        role VARCHAR(32) NOT NULL DEFAULT 'researcher',
                        password_hash VARCHAR(255) NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                    """
                )

                # 2. Research Tasks Table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS research_tasks (
                        task_id VARCHAR(64) PRIMARY KEY,
                        thread_id VARCHAR(64) UNIQUE NOT NULL,
                        topic TEXT NOT NULL,
                        user_id VARCHAR(64),
                        user_name VARCHAR(255),
                        status VARCHAR(64) NOT NULL DEFAULT 'running',
                        current_step VARCHAR(64) NOT NULL DEFAULT 'planning',
                        is_running BOOLEAN NOT NULL DEFAULT TRUE,
                        is_pending_review BOOLEAN NOT NULL DEFAULT FALSE,
                        evidence_count INT NOT NULL DEFAULT 0,
                        has_report BOOLEAN NOT NULL DEFAULT FALSE,
                        error TEXT,
                        created_at DOUBLE PRECISION NOT NULL,
                        updated_at DOUBLE PRECISION NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_research_tasks_user_id ON research_tasks(user_id);
                    CREATE INDEX IF NOT EXISTS idx_research_tasks_created_at ON research_tasks(created_at DESC);
                    """
                )

                # 3. Seed demo accounts if empty
                if demo_accounts:
                    cur.execute("SELECT COUNT(*) AS count FROM users")
                    row = cur.fetchone()
                    if row and row["count"] == 0:
                        now = time.time()
                        for demo in demo_accounts:
                            cur.execute(
                                """
                                INSERT INTO users (id, email, name, role, password_hash, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (email) DO NOTHING
                                """,
                                (
                                    str(uuid.uuid4()),
                                    demo["email"].lower(),
                                    demo["name"],
                                    demo["role"],
                                    demo["password_hash"],
                                    now,
                                ),
                            )
                conn.commit()

        # 4. LangGraph Checkpointer schema
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            with PostgresSaver.from_conn_string(POSTGRES_URL) as cp:
                cp.setup()
        except Exception as exc:
            logger.warning("PostgresSaver setup encountered notice: %s", exc)

        logger.info("PostgreSQL schema successfully initialized on %s", POSTGRES_URL)
        return True
    except Exception as exc:
        logger.error("Failed to initialize PostgreSQL schema: %s", exc)
        return False


# ──────────────────────────────────────────────
# User Persistence Helpers (PostgreSQL)
# ──────────────────────────────────────────────
def pg_get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user dictionary by email from PostgreSQL."""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
                return cur.fetchone()
    except Exception as exc:
        logger.error("pg_get_user_by_email failed: %s", exc)
        return None


def pg_get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user dictionary by ID from PostgreSQL."""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                return cur.fetchone()
    except Exception as exc:
        logger.error("pg_get_user_by_id failed: %s", exc)
        return None


def pg_create_user(user_dict: Dict[str, Any]) -> bool:
    """Insert a new user account into PostgreSQL. Raises ValueError on duplicate email."""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, name, role, password_hash, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_dict["id"],
                        user_dict["email"].lower(),
                        user_dict["name"],
                        user_dict["role"],
                        user_dict["password_hash"],
                        user_dict["created_at"],
                    ),
                )
                conn.commit()
        return True
    except UniqueViolation:
        raise ValueError("A user with this email already exists.")
    except Exception as exc:
        logger.error("pg_create_user failed: %s", exc)
        return False


# ──────────────────────────────────────────────
# Task Persistence Helpers (PostgreSQL)
# ──────────────────────────────────────────────
def pg_save_task(task_dict: Dict[str, Any]) -> bool:
    """Upsert a research task record in PostgreSQL."""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO research_tasks (
                        task_id, thread_id, topic, user_id, user_name,
                        status, current_step, is_running, is_pending_review,
                        evidence_count, has_report, error, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (thread_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        current_step = EXCLUDED.current_step,
                        is_running = EXCLUDED.is_running,
                        is_pending_review = EXCLUDED.is_pending_review,
                        evidence_count = EXCLUDED.evidence_count,
                        has_report = EXCLUDED.has_report,
                        error = EXCLUDED.error,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        task_dict.get("task_id", task_dict.get("thread_id")),
                        task_dict.get("thread_id"),
                        task_dict.get("topic"),
                        task_dict.get("user_id"),
                        task_dict.get("user_name"),
                        task_dict.get("status", "running"),
                        task_dict.get("current_step", "planning"),
                        task_dict.get("is_running", True),
                        task_dict.get("is_pending_review", False),
                        task_dict.get("evidence_count", 0),
                        task_dict.get("has_report", False),
                        task_dict.get("error"),
                        task_dict.get("created_at", time.time()),
                        task_dict.get("updated_at", time.time()),
                    ),
                )
                conn.commit()
        return True
    except Exception as exc:
        logger.error("pg_save_task failed: %s", exc)
        return False


def pg_get_task(thread_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve task dictionary by thread_id from PostgreSQL."""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM research_tasks WHERE thread_id = %s", (thread_id,))
                return cur.fetchone()
    except Exception as exc:
        logger.error("pg_get_task failed: %s", exc)
        return None


def pg_list_tasks(user_id: Optional[str] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
    """List task dictionaries from PostgreSQL."""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                if is_admin or not user_id:
                    cur.execute("SELECT * FROM research_tasks ORDER BY created_at DESC")
                else:
                    cur.execute(
                        "SELECT * FROM research_tasks WHERE user_id = %s ORDER BY created_at DESC",
                        (user_id,),
                    )
                return cur.fetchall()
    except Exception as exc:
        logger.error("pg_list_tasks failed: %s", exc)
        return []


def pg_delete_task(thread_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> bool:
    """Delete a task record from PostgreSQL."""
    try:
        with get_postgres_conn() as conn:
            with conn.cursor() as cur:
                if is_admin or not user_id:
                    cur.execute("DELETE FROM research_tasks WHERE thread_id = %s", (thread_id,))
                else:
                    cur.execute(
                        "DELETE FROM research_tasks WHERE thread_id = %s AND user_id = %s",
                        (thread_id, user_id),
                    )
                conn.commit()
                return cur.rowcount > 0
    except Exception as exc:
        logger.error("pg_delete_task failed: %s", exc)
        return False
