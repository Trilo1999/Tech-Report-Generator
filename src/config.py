"""
Centralized configuration for the AI Research & Report Generation Agent.

Supports both containerized services (Docker Qdrant & PostgreSQL) and local embedded mode.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample_data"
QDRANT_STORAGE_DIR = DATA_DIR / "qdrant_storage"
CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints.db"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Sample data file paths
BENCHMARK_CSV = SAMPLE_DATA_DIR / "benchmark_results.csv"
CLOUD_PRICING_JSON = SAMPLE_DATA_DIR / "cloud_pricing.json"
RESEARCH_SOURCES_JSON = SAMPLE_DATA_DIR / "research_sources.json"
ARCHITECTURE_GUIDELINES_MD = SAMPLE_DATA_DIR / "architecture_guidelines.md"
DATABASE_COMPARISON_PDF = SAMPLE_DATA_DIR / "database_comparison.pdf"

# ──────────────────────────────────────────────
# Qdrant Vector DB Configuration
# ──────────────────────────────────────────────
QDRANT_COLLECTION_NAME = "research_documents"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Docker / Remote Qdrant connection URL
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
# Force local embedded storage (auto-fallback if Qdrant URL is unreachable)
QDRANT_PREFER_EMBEDDED = os.getenv("QDRANT_PREFER_EMBEDDED", "false").lower() == "true"

# ──────────────────────────────────────────────
# Persistence & Checkpointing
# ──────────────────────────────────────────────
# Docker PostgreSQL connection URL
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgrespassword@localhost:5432/research_agent")
# SQLite local file fallback
SQLITE_DB_URL = f"sqlite:///{CHECKPOINT_DB_PATH}"

# ──────────────────────────────────────────────
# LLM & Observability
# ──────────────────────────────────────────────
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
LLM_TEMPERATURE = 0.2  # Low temperature for factual, deterministic outputs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ──────────────────────────────────────────────
# Agent Workflow Constants
# ──────────────────────────────────────────────
MAX_RESEARCH_ITERATIONS = 2  # Max re-search loops before forcing draft
MIN_SUBQUESTIONS = 3  # Minimum subquestions the planner must generate
TOP_K_SEARCH_RESULTS = 5  # Number of Qdrant results per query

# ──────────────────────────────────────────────
# Server Configuration
# ──────────────────────────────────────────────
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# ──────────────────────────────────────────────
# Convenience Settings Object
# ──────────────────────────────────────────────


class Settings:
    """Convenience wrapper — print to verify configuration."""

    def __repr__(self) -> str:
        return (
            f"Settings(\n"
            f"  PROJECT_ROOT       = {PROJECT_ROOT}\n"
            f"  SAMPLE_DATA_DIR    = {SAMPLE_DATA_DIR}\n"
            f"  QDRANT_URL         = {QDRANT_URL}\n"
            f"  POSTGRES_URL       = {POSTGRES_URL}\n"
            f"  QDRANT_STORAGE     = {QDRANT_STORAGE_DIR}\n"
            f"  CHECKPOINT_DB      = {CHECKPOINT_DB_PATH}\n"
            f"  REPORTS_DIR        = {REPORTS_DIR}\n"
            f"  EMBEDDING_MODEL    = {EMBEDDING_MODEL_NAME}\n"
            f"  LLM_MODEL          = {LLM_MODEL_NAME}\n"
            f"  MAX_ITERATIONS     = {MAX_RESEARCH_ITERATIONS}\n"
            f"  CHUNK_SIZE         = {CHUNK_SIZE}\n"
            f")"
        )


settings = Settings()
