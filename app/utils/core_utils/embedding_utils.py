import asyncio
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


def _build_fastembed_wrapper(model_name: str) -> Any:
    """Build a fastembed-based fallback embedding instance."""
    from fastembed import TextEmbedding

    class _FastEmbedWrapper:
        def __init__(self, name: str):
            self.model = TextEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [e.tolist() for e in self.model.embed(texts)]

        def embed_query(self, text: str) -> list[float]:
            return list(self.model.embed([text]))[0].tolist()

        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            return await asyncio.to_thread(self.embed_documents, texts)

        async def aembed_query(self, text: str) -> list[float]:
            return await asyncio.to_thread(self.embed_query, text)

    return _FastEmbedWrapper(model_name)


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
        try:
            import sentence_transformers  # noqa: F401

            has_sentence_transformers = True
        except ImportError:
            has_sentence_transformers = False

        if not has_sentence_transformers or HuggingFaceEmbeddings is None:
            return _build_fastembed_wrapper(self.embedding_model_name)

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
            logger.info("Embedding model loaded.")
            return model
        except Exception as exc:
            logger.warning(
                "Could not load HuggingFaceEmbeddings (%s); falling back to FastEmbed.",
                exc,
            )
            return _build_fastembed_wrapper(self.embedding_model_name)


class _LazyEmbeddingClient:
    """Lazy proxy so embedding model is not loaded at module import time."""

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = EmbeddingClient().create_embeddings()
        return self._client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._get_client().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._get_client().embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Asynchronously compute embeddings for documents in a worker thread.

        Prevents blocking the main asyncio event loop during vectorization.
        """
        client = self._get_client()
        if hasattr(client, "aembed_documents") and callable(client.aembed_documents):
            import inspect

            if inspect.iscoroutinefunction(client.aembed_documents):
                return await client.aembed_documents(texts)
        return await asyncio.to_thread(self.embed_documents, texts)

    async def aembed_query(self, text: str) -> list[float]:
        """Asynchronously compute embedding for a query in a worker thread.

        Prevents blocking the main asyncio event loop during vectorization.
        """
        client = self._get_client()
        if hasattr(client, "aembed_query") and callable(client.aembed_query):
            import inspect

            if inspect.iscoroutinefunction(client.aembed_query):
                return await client.aembed_query(text)
        return await asyncio.to_thread(self.embed_query, text)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_client(), name)


embeddings_client = _LazyEmbeddingClient()
