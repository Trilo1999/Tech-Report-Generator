"""Core (product) services: cache, report, task, research, ingestion, retrieval."""

from app.services.core_services.cache_service import CacheService, cache_service
from app.services.core_services.ingestion_service import IngestionService
from app.services.core_services.report_service import ReportService
from app.services.core_services.research_service import ResearchService
from app.services.core_services.retrieval_service import VectorRetriever
from app.services.core_services.task_service import TaskManager

__all__ = [
    "CacheService",
    "cache_service",
    "IngestionService",
    "ReportService",
    "ResearchService",
    "VectorRetriever",
    "TaskManager",
]
