"""
Centralized configuration for the AI Research & Report Generation Agent.

Supports both containerized services (Docker Qdrant & PostgreSQL) and local embedded mode.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample_data"
QDRANT_STORAGE_DIR = DATA_DIR / "qdrant_storage"
CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints.db"
AUTH_DB_PATH = DATA_DIR / "users.db"
FASTEMBED_CACHE_DIR = DATA_DIR / "cache"
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
# LLM & Observability (Hive AI, Google Gemini, OpenAI)
# ──────────────────────────────────────────────
HIVE_SECRET_KEY = os.getenv("HIVE_SECRET_KEY", os.getenv("HIVE_API_KEY", ""))
HIVE_REGIONAL_COMPLIANCE = os.getenv("HIVE_REGIONAL_COMPLIANCE", "false").lower() == "true"
HIVE_BASE_URL = os.getenv(
    "HIVE_BASE_URL",
    "https://api-va1.deploy.com/api/v1" if HIVE_REGIONAL_COMPLIANCE else "https://api-cdn.deploy.com/api/v1",
)
HIVE_MODEL_NAME = os.getenv("HIVE_MODEL_NAME", "deepseek-ai/deepseek-v4.1-flash-1017")


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if HIVE_SECRET_KEY:
    _default_provider = "hive"
    _default_model = HIVE_MODEL_NAME
elif GOOGLE_API_KEY:
    _default_provider = "google"
    _default_model = "gemini-3-flash-preview"
else:
    _default_provider = "openai"
    _default_model = "gpt-4o-mini"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", _default_provider).lower()
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", _default_model)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# ──────────────────────────────────────────────
# Agent Workflow Constants
# ──────────────────────────────────────────────
MAX_RESEARCH_ITERATIONS = 2  # Max re-search loops before forcing draft
MIN_SUBQUESTIONS = 3  # Minimum subquestions the planner must generate
TOP_K_SEARCH_RESULTS = 5  # Number of Qdrant results per query

# ──────────────────────────────────────────────
# Authentication & RBAC Configuration
# ──────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "antigravity-research-agent-insecure-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

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
