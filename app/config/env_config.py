import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Load and expose environment settings for the application."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        # 1. Project information
        self.ENV: str = os.getenv("ENV", "dev")
        self.PROJECT_NAME: str = os.getenv(
            "PROJECT_NAME", "AI-Research-Report-Generation-Agent"
        )
        self.PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "2.0.0")
        self.PROJECT_DESCRIPTION: str = os.getenv(
            "PROJECT_DESCRIPTION",
            "Agentic technical research, deterministic data analysis, human-in-the-loop review, and publication export.",
        )

        # 2. Paths
        self.PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
        self.APP_DIR = Path(__file__).resolve().parent.parent
        self.SAMPLE_DATA_DIR = self.APP_DIR / "sample_docs"
        self.DATA_DIR = self.APP_DIR / "data"
        self.QDRANT_STORAGE_DIR = self.DATA_DIR / "qdrant_storage"
        self.CHECKPOINT_DB_PATH = self.DATA_DIR / "checkpoints.db"
        self.AUTH_DB_PATH = self.DATA_DIR / "users.db"
        self.FASTEMBED_CACHE_DIR = self.DATA_DIR / "cache"
        self.REPORTS_DIR = self.APP_DIR / "reports"

        self.BENCHMARK_CSV = self.SAMPLE_DATA_DIR / "benchmark_results.csv"
        self.CLOUD_PRICING_JSON = self.SAMPLE_DATA_DIR / "cloud_pricing.json"
        self.RESEARCH_SOURCES_JSON = self.SAMPLE_DATA_DIR / "research_sources.json"
        self.ARCHITECTURE_GUIDELINES_MD = (
            self.SAMPLE_DATA_DIR / "architecture_guidelines.md"
        )
        self.DATABASE_COMPARISON_PDF = self.SAMPLE_DATA_DIR / "database_comparison.pdf"

        # 3. API configuration
        self.ALLOWED_ORIGINS: list[str] = [
            o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
        ]
        self.BASE_PATH: str = os.getenv("BASE_PATH", "")
        self.OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY", None)
        self.GEMINI_API_KEY: str | None = os.getenv(
            "GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", None)
        )

        # 4. Hive AI and LLM Provider Settings
        self.HIVE_SECRET_KEY: str = os.getenv(
            "HIVE_SECRET_KEY", os.getenv("HIVE_API_KEY", "")
        )
        self.HIVE_REGIONAL_COMPLIANCE: bool = (
            os.getenv("HIVE_REGIONAL_COMPLIANCE", "false").lower() == "true"
        )
        self.HIVE_BASE_URL: str = os.getenv(
            "HIVE_BASE_URL",
            (
                "https://api-regional.deploy.com/api/v1"
                if self.HIVE_REGIONAL_COMPLIANCE
                else "https://api-cdn.deploy.com/api/v1"
            ),
        )
        self.HIVE_MODEL_NAME: str = os.getenv(
            "HIVE_MODEL_NAME", "deepseek-ai/deepseek-v4.1-flash-1017"
        )

        if self.HIVE_SECRET_KEY:
            default_provider = "hive"
            default_model = self.HIVE_MODEL_NAME
        elif self.GEMINI_API_KEY:
            default_provider = "google"
            default_model = "gemini-3-flash-preview"
        else:
            default_provider = "openai"
            default_model = "gpt-4o-mini"

        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", default_provider).lower()
        self.LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", default_model)
        self.LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

        # 5. Authentication configuration
        self.JWT_SECRET_KEY: str = os.getenv(
            "JWT_SECRET_KEY", "agentic-web-starter-jwt"
        )
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )

        # 6. Admin configuration
        self.ADMIN_USERNAME: str | None = (
            os.getenv("ADMIN_USERNAME", "admin").strip() or None
        )
        self.ADMIN_EMAIL: str | None = (
            os.getenv("ADMIN_EMAIL", "admin@antigravity.ai").strip() or None
        )
        self.ADMIN_PASSWORD: str | None = (
            os.getenv("ADMIN_PASSWORD", "Admin@123").strip() or None
        )

        # 7. Working directory
        working_dir = os.path.abspath(os.getenv("WORKING_DIR", "app").strip() or "app")
        self.WORKING_PROJECT_DIR: str = os.path.join(working_dir, self.PROJECT_NAME)
        self.DB_PATH: str = os.path.join(working_dir, "sqlite_data", "app.db")
        self.LOG_DIR: str = os.path.join(self.WORKING_PROJECT_DIR, "logs")
        self.UPLOAD_DIR: str = os.path.join(
            self.WORKING_PROJECT_DIR, "static", "uploads"
        )

        # 8. Hugging Face & Embeddings
        self.HF_HOME: str = os.getenv(
            "HF_HOME", os.path.join(self.WORKING_PROJECT_DIR, "hf")
        )
        os.environ.setdefault("HF_HOME", self.HF_HOME)
        self.EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
        self.EMBEDDING_DIMENSION: int = 384
        self.CHUNK_SIZE: int = 500
        self.CHUNK_OVERLAP: int = 100

        # 9. Qdrant configuration
        self.COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "research_documents")
        self.QDRANT_COLLECTION_NAME: str = self.COLLECTION_NAME
        self.USE_QDRANT: bool = (
            os.getenv("USE_QDRANT", "true").strip().lower() == "true"
        )
        self.USE_REDIS: bool = os.getenv("USE_REDIS", "true").strip().lower() == "true"
        self.USE_SQL: bool = os.getenv("USE_SQL", "true").strip().lower() == "true"

        self.QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.QDRANT_PREFER_EMBEDDED: bool = (
            os.getenv("QDRANT_PREFER_EMBEDDED", "false").lower() == "true"
        )
        self.QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
        self.QDRANT_PORT: str = os.getenv("QDRANT_PORT", "6333")
        self.QDRANT_PROTOCOL: str = os.getenv("QDRANT_PROTOCOL", "http")

        # 10. Persistence & Checkpointing
        self.POSTGRES_URL: str = os.getenv(
            "POSTGRES_URL",
            "postgresql://postgres:postgrespassword@localhost:5432/research_agent",
        )
        self.SQLITE_DB_URL: str = f"sqlite:///{self.CHECKPOINT_DB_PATH}"

        # 11. Workflow Constants
        self.MAX_RESEARCH_ITERATIONS: int = 2
        self.MIN_SUBQUESTIONS: int = 3
        self.TOP_K_SEARCH_RESULTS: int = 5

        # 12. Redis configuration (optional)
        self.REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
        self.REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
        self.REDIS_PROTOCOL: str = os.getenv("REDIS_PROTOCOL", "http")
        self.REDIS_DB: str = os.getenv("REDIS_DB", "0")

        # 13. RabbitMQ configuration (optional)
        self.USE_RABBITMQ: bool = (
            os.getenv("USE_RABBITMQ", "true").strip().lower() == "true"
        )
        self.RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.RABBITMQ_USERNAME: str = os.getenv("RABBITMQ_USERNAME", "guest")
        self.RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
        self.RABBITMQ_AMQP_URL: str | None = (
            os.getenv("RABBITMQ_AMQP_URL", "").strip() or None
        )
        self.RABBITMQ_INGEST_QUEUE: str = os.getenv(
            "RABBITMQ_INGEST_QUEUE", "agentic_web_starter.ingestion"
        )

        # 14. Server configuration
        self.SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
        self.SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

        # 15. LangSmith Tracing
        self.LANGSMITH_TRACING: bool = (
            os.getenv(
                "LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false")
            ).lower()
            == "true"
        )
        self.LANGSMITH_API_KEY: str = os.getenv(
            "LANGSMITH_API_KEY", os.getenv("LANGCHAIN_API_KEY", "")
        )
        self.LANGSMITH_PROJECT: str = os.getenv(
            "LANGSMITH_PROJECT",
            os.getenv("LANGCHAIN_PROJECT", "ai-research-report-agent"),
        )
        if self.LANGSMITH_TRACING and self.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = self.LANGSMITH_PROJECT

    def __repr__(self) -> str:
        return (
            f"Settings(\n"
            f"  PROJECT_ROOT       = {self.PROJECT_ROOT}\n"
            f"  SAMPLE_DATA_DIR    = {self.SAMPLE_DATA_DIR}\n"
            f"  QDRANT_URL         = {self.QDRANT_URL}\n"
            f"  POSTGRES_URL       = {self.POSTGRES_URL}\n"
            f"  QDRANT_STORAGE     = {self.QDRANT_STORAGE_DIR}\n"
            f"  CHECKPOINT_DB      = {self.CHECKPOINT_DB_PATH}\n"
            f"  REPORTS_DIR        = {self.REPORTS_DIR}\n"
            f"  EMBEDDING_MODEL    = {self.EMBEDDING_MODEL_NAME}\n"
            f"  LLM_MODEL          = {self.LLM_MODEL_NAME}\n"
            f"  MAX_ITERATIONS     = {self.MAX_RESEARCH_ITERATIONS}\n"
            f"  CHUNK_SIZE         = {self.CHUNK_SIZE}\n"
            f")"
        )


settings = Settings()

# Module-level convenience exports for seamless direct access
PROJECT_ROOT = settings.PROJECT_ROOT
DATA_DIR = settings.DATA_DIR
SAMPLE_DATA_DIR = settings.SAMPLE_DATA_DIR
QDRANT_STORAGE_DIR = settings.QDRANT_STORAGE_DIR
CHECKPOINT_DB_PATH = settings.CHECKPOINT_DB_PATH
AUTH_DB_PATH = settings.AUTH_DB_PATH
FASTEMBED_CACHE_DIR = settings.FASTEMBED_CACHE_DIR
REPORTS_DIR = settings.REPORTS_DIR
BENCHMARK_CSV = settings.BENCHMARK_CSV
CLOUD_PRICING_JSON = settings.CLOUD_PRICING_JSON
RESEARCH_SOURCES_JSON = settings.RESEARCH_SOURCES_JSON
ARCHITECTURE_GUIDELINES_MD = settings.ARCHITECTURE_GUIDELINES_MD
DATABASE_COMPARISON_PDF = settings.DATABASE_COMPARISON_PDF
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS
BASE_PATH = settings.BASE_PATH
OPENAI_API_KEY = settings.OPENAI_API_KEY
GEMINI_API_KEY = settings.GEMINI_API_KEY
HIVE_SECRET_KEY = settings.HIVE_SECRET_KEY
HIVE_BASE_URL = settings.HIVE_BASE_URL
HIVE_MODEL_NAME = settings.HIVE_MODEL_NAME
LLM_PROVIDER = settings.LLM_PROVIDER
LLM_MODEL_NAME = settings.LLM_MODEL_NAME
EMBEDDING_MODEL_NAME = settings.EMBEDDING_MODEL_NAME
EMBEDDING_DIMENSION = settings.EMBEDDING_DIMENSION
CHUNK_SIZE = settings.CHUNK_SIZE
CHUNK_OVERLAP = settings.CHUNK_OVERLAP
COLLECTION_NAME = settings.COLLECTION_NAME
QDRANT_COLLECTION_NAME = settings.QDRANT_COLLECTION_NAME
USE_QDRANT = settings.USE_QDRANT
USE_REDIS = settings.USE_REDIS
USE_SQL = settings.USE_SQL
QDRANT_URL = settings.QDRANT_URL
QDRANT_PREFER_EMBEDDED = settings.QDRANT_PREFER_EMBEDDED
QDRANT_HOST = settings.QDRANT_HOST
QDRANT_PORT = settings.QDRANT_PORT
QDRANT_PROTOCOL = settings.QDRANT_PROTOCOL
POSTGRES_URL = settings.POSTGRES_URL
MAX_RESEARCH_ITERATIONS = settings.MAX_RESEARCH_ITERATIONS
MIN_SUBQUESTIONS = settings.MIN_SUBQUESTIONS
TOP_K_SEARCH_RESULTS = settings.TOP_K_SEARCH_RESULTS
REDIS_HOST = settings.REDIS_HOST
REDIS_PORT = settings.REDIS_PORT
REDIS_DB = settings.REDIS_DB
REDIS_PROTOCOL = settings.REDIS_PROTOCOL
USE_RABBITMQ = settings.USE_RABBITMQ
RABBITMQ_HOST = settings.RABBITMQ_HOST
RABBITMQ_PORT = settings.RABBITMQ_PORT
RABBITMQ_USERNAME = settings.RABBITMQ_USERNAME
RABBITMQ_PASSWORD = settings.RABBITMQ_PASSWORD
RABBITMQ_VHOST = settings.RABBITMQ_VHOST
RABBITMQ_AMQP_URL = settings.RABBITMQ_AMQP_URL
RABBITMQ_INGEST_QUEUE = settings.RABBITMQ_INGEST_QUEUE
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
ADMIN_USERNAME = settings.ADMIN_USERNAME
ADMIN_EMAIL = settings.ADMIN_EMAIL
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
SERVER_HOST = settings.SERVER_HOST
SERVER_PORT = settings.SERVER_PORT
LANGSMITH_TRACING = settings.LANGSMITH_TRACING
LANGSMITH_API_KEY = settings.LANGSMITH_API_KEY
LANGSMITH_PROJECT = settings.LANGSMITH_PROJECT
