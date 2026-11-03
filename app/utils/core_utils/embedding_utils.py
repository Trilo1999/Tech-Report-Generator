from typing import Any

from app.config.log_config import logger
from app.constants.app_constants import VECTOR_DB

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain_community.embeddings import (
            FastEmbedEmbeddings as HuggingFaceEmbeddings,
        )
    except ImportError:
        HuggingFaceEmbeddings = None


class EmbeddingClient:
    """Factory for embeddings clients."""

    def __init__(
        self, embedding_model_name: str = VECTOR_DB.EMBEDDING_MODEL.value
    ) -> None:
        """Initialize the embedding client.

        Args:
            embedding_model_name: Hugging Face model name. Defaults to VECTOR_DB setting.
        """
        self.embedding_model_name = embedding_model_name

    def create_embeddings(self) -> Any:
        """Create embeddings client for the vector database.

        Returns:
            Embeddings instance configured for the model.
        """
        if HuggingFaceEmbeddings is None:
            from fastembed import TextEmbedding

            class _FastEmbedWrapper:
                def __init__(self, model_name: str):
                    self.model = TextEmbedding(
                        model_name="sentence-transformers/all-MiniLM-L6-v2"
                    )

                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    return [e.tolist() for e in self.model.embed(texts)]

                def embed_query(self, text: str) -> list[float]:
                    return list(self.model.embed([text]))[0].tolist()

            return _FastEmbedWrapper(self.embedding_model_name)

        encode_kwargs = {"normalize_embeddings": True}

        logger.info(
            "Loading embedding model %s (first run may download from Hugging Face)...",
            self.embedding_model_name,
        )

        try:
            model = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                encode_kwargs=encode_kwargs,
            )
        except Exception:
            try:
                model = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
            except Exception:
                model = HuggingFaceEmbeddings()
        logger.info("Embedding model loaded.")
        return model


embeddings_client = EmbeddingClient().create_embeddings()
