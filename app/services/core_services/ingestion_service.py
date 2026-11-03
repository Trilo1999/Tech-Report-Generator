from typing import Any, Dict, Optional

from fastapi import UploadFile

from app.config.log_config import logger
from app.exceptions import InternalError, ValidationError
from app.tools.indexer_tool import IndexerTool
from app.utils.core_utils import FileProcessor


class IngestionService:
    """Stateless service for file storage and indexing. Use the module-level instance."""

    def save_file(self, file: UploadFile) -> str:
        """Save the file to the upload directory.

        Args:
            file: The uploaded file to save.

        Returns:
            Path where file was saved.

        Raises:
            ValidationError: If file save fails.
            InternalError: If unexpected error occurs.
        """
        try:
            file_processor = FileProcessor(file=file)
            file_path = file_processor.get_file_path()
            saved_path = file_processor.save_file(file_path)
            logger.info("File saved successfully at: %s", saved_path)
            return saved_path
        except (OSError, IOError) as e:
            logger.exception("File save failed: %s", e)
            raise ValidationError("File save failed") from e
        except Exception as e:
            logger.exception("Unexpected error saving file: %s", e)
            raise InternalError("File upload failed") from e

    def ingest_file(self, file: UploadFile, saved_path: Optional[str] = None) -> Dict[str, Any]:
        """Save the file (if needed) and index it into the vector database.

        Args:
            file: The uploaded file.
            saved_path: Optional pre-saved file path; if None, file is saved first.

        Returns:
            Dict with saved_path and index_result.

        Raises:
            ValidationError: If file handling fails.
            InternalError: If ingestion/indexing fails.
        """
        try:
            if saved_path is None:
                saved_path = self.save_file(file)

            index_result = self.index_file(saved_path)
            return {"saved_path": saved_path, "index_result": index_result}
        except (ValidationError, InternalError):
            raise
        except Exception as e:
            logger.exception("Ingestion/indexing failed: %s", e)
            raise InternalError("File ingestion failed") from e

    def index_file(self, filepath: str) -> Any:
        """Index an already-saved file into the vector database (e.g. for workers).

        Args:
            filepath: Path to the saved file.

        Returns:
            Index tool result.
        """
        try:
            index_tool = IndexerTool(filepath=filepath)
            return index_tool._run()
        except Exception as e:
            logger.exception("Indexing failed for filepath=%s: %s", filepath, e)
            raise InternalError("File ingestion failed") from e

    @classmethod
    async def trigger_document_ingestion(cls, current_user: Any) -> Dict[str, Any]:
        """Trigger document parsing, chunking, and vector indexing into Qdrant."""
        import asyncio
        from fastapi import HTTPException
        from app.services.core_services.qdrant_ingestion import (
            QDRANT_COLLECTION_NAME,
            get_qdrant_client,
            ingest_all_documents,
        )

        try:
            total_indexed = await asyncio.to_thread(ingest_all_documents, force_recreate=True)
            client = get_qdrant_client()
            info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
            email = getattr(current_user, "email", str(current_user))
            return {
                "status": "success",
                "message": "Document ingestion and vector indexing completed successfully.",
                "collection_name": QDRANT_COLLECTION_NAME,
                "points_indexed": total_indexed,
                "total_points": info.points_count or total_indexed,
                "triggered_by": email,
            }
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion pipeline failed: {str(exc)}",
            ) from exc

    @classmethod
    def get_ingestion_status(cls) -> Dict[str, Any]:
        """Inspect the current Qdrant vector database collection status and indexed point count."""
        from fastapi import HTTPException
        from app.services.core_services.qdrant_ingestion import (
            QDRANT_COLLECTION_NAME,
            get_qdrant_client,
        )

        try:
            client = get_qdrant_client()
            info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
            return {
                "collection_name": QDRANT_COLLECTION_NAME,
                "status": str(info.status),
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
            }
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch Qdrant status: {str(exc)}",
            ) from exc


# Singleton instance for use when USE_QDRANT (or other env) enables ingestion.
ingestion_service = IngestionService()
trigger_document_ingestion = IngestionService.trigger_document_ingestion
get_ingestion_status = IngestionService.get_ingestion_status
