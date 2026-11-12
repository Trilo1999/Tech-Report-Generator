"""
Qdrant Document Ingestion Pipeline & Metadata Indexing implementing OOP patterns.

Parses database_comparison.pdf and architecture_guidelines.md, applies context-aware
sliding-window chunking, generates 384-dimensional dense vectors with all-MiniLM-L6-v2,
and indexes them into Qdrant with searchable metadata payloads.
"""

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastembed import TextEmbedding
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    PayloadSchemaType,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from app.config.env_config import (
    ARCHITECTURE_GUIDELINES_MD,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATABASE_COMPARISON_PDF,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_NAME,
    FASTEMBED_CACHE_DIR,
    QDRANT_COLLECTION_NAME,
    QDRANT_PREFER_EMBEDDED,
    QDRANT_STORAGE_DIR,
    QDRANT_URL,
)


class QdrantDocumentIngestor:
    """Object-oriented document ingestion, chunking, and semantic vector indexing pipeline."""

    def __init__(
        self,
        collection_name: str = QDRANT_COLLECTION_NAME,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        vector_size: int = EMBEDDING_DIMENSION,
    ):
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_size = vector_size
        self._embedding_model: Optional[TextEmbedding] = None
        self._qdrant_client: Optional[QdrantClient] = None

    def get_embedding_model(self) -> TextEmbedding:
        """Return a cached instance of the FastEmbed model (all-MiniLM-L6-v2)."""
        if self._embedding_model is None:
            model_name = f"sentence-transformers/{EMBEDDING_MODEL_NAME}"
            cache_dir_str = (
                str(FASTEMBED_CACHE_DIR) if FASTEMBED_CACHE_DIR.exists() else None
            )
            self._embedding_model = TextEmbedding(
                model_name=model_name, cache_dir=cache_dir_str
            )
        return self._embedding_model

    def get_client(self, reconnect: bool = False) -> QdrantClient:
        """
        Connect to Qdrant with dual-mode flexibility:
        1. Try Docker container / remote URL (default: http://localhost:6333)
        2. Fall back to local embedded storage if unreachable or explicitly requested.
        """
        if self._qdrant_client is not None and not reconnect:
            return self._qdrant_client

        if not QDRANT_PREFER_EMBEDDED:
            try:
                client = QdrantClient(
                    url=QDRANT_URL, timeout=3.0, check_compatibility=False
                )
                client.get_collections()
                self._qdrant_client = client
                return self._qdrant_client
            except Exception:
                pass

        QDRANT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self._qdrant_client = QdrantClient(
            path=str(QDRANT_STORAGE_DIR), check_compatibility=False
        )
        return self._qdrant_client

    def chunk_text(
        self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None
    ) -> List[str]:
        """Split text into overlapping windows to preserve context across boundaries."""
        eff_chunk_size = chunk_size if chunk_size is not None else self.chunk_size
        eff_overlap = overlap if overlap is not None else self.chunk_overlap

        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []

        if len(cleaned) <= eff_chunk_size:
            return [cleaned]

        chunks: List[str] = []
        start = 0
        step = eff_chunk_size - eff_overlap

        while start < len(cleaned):
            end = start + eff_chunk_size
            chunk = cleaned[start:end].strip()
            if len(chunk) >= 40:
                chunks.append(chunk)
            start += step

        return chunks

    def parse_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract text page-by-page from a PDF, identifying section headings and chunking."""
        if not file_path.is_file():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        reader = PdfReader(str(file_path))
        extracted_sections: List[Dict[str, Any]] = []

        top_heading_pattern = re.compile(r"^(\d+\.\s+[A-Za-z0-9\s—–\-]+)")
        sub_heading_pattern = re.compile(r"^(\d+\.\d+\s+[A-Za-z0-9\s—–\-]+)")

        parent_section = "General Overview"
        current_section = "General Overview"
        current_text: List[str] = []

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            lines = page_text.splitlines()

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                top_match = top_heading_pattern.match(line_str)
                sub_match = sub_heading_pattern.match(line_str)

                if (top_match or sub_match) and len(line_str) < 80:
                    if current_text:
                        section_body = " ".join(current_text).strip()
                        if section_body:
                            extracted_sections.append(
                                {
                                    "section": current_section,
                                    "text": section_body,
                                    "source_file": file_path.name,
                                    "doc_type": "pdf",
                                    "page": page_num,
                                }
                            )
                        current_text = []

                    if top_match:
                        parent_section = top_match.group(1).strip()
                        current_section = parent_section
                    elif sub_match:
                        current_section = (
                            f"{parent_section} > {sub_match.group(1).strip()}"
                        )
                else:
                    current_text.append(line_str)

        if current_text:
            section_body = " ".join(current_text).strip()
            if section_body:
                extracted_sections.append(
                    {
                        "section": current_section,
                        "text": section_body,
                        "source_file": file_path.name,
                        "doc_type": "pdf",
                        "page": len(reader.pages),
                    }
                )

        return extracted_sections

    def parse_markdown(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse markdown file preserving hierarchical header hierarchy (# H1, ## H2, ### H3)."""
        if not file_path.is_file():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        h1_pattern = re.compile(r"^#\s+(.+)$")
        h2_pattern = re.compile(r"^##\s+(.+)$")
        h3_pattern = re.compile(r"^###\s+(.+)$")

        current_h1 = "Architecture Guidelines"
        current_h2 = ""
        current_h3 = ""
        current_text: List[str] = []
        extracted_sections: List[Dict[str, Any]] = []

        def get_current_section_name() -> str:
            parts = [p for p in [current_h1, current_h2, current_h3] if p]
            return " > ".join(parts) if parts else "Architecture Guidelines"

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            h1_m = h1_pattern.match(line_str)
            h2_m = h2_pattern.match(line_str)
            h3_m = h3_pattern.match(line_str)

            if h1_m or h2_m or h3_m:
                if current_text:
                    body = " ".join(current_text).strip()
                    if body:
                        extracted_sections.append(
                            {
                                "section": get_current_section_name(),
                                "text": body,
                                "source_file": file_path.name,
                                "doc_type": "guideline",
                            }
                        )
                    current_text = []

                if h1_m:
                    current_h1 = h1_m.group(1).strip()
                    current_h2 = ""
                    current_h3 = ""
                elif h2_m:
                    current_h2 = h2_m.group(1).strip()
                    current_h3 = ""
                elif h3_m:
                    current_h3 = h3_m.group(1).strip()
            else:
                current_text.append(line_str)

        if current_text:
            body = " ".join(current_text).strip()
            if body:
                extracted_sections.append(
                    {
                        "section": get_current_section_name(),
                        "text": body,
                        "source_file": file_path.name,
                        "doc_type": "guideline",
                    }
                )

        return extracted_sections

    def create_or_recreate_collection(
        self,
        client: QdrantClient,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        force_recreate: bool = True,
    ) -> None:
        """Initialize collection with Cosine distance and create payload indexes for fast filtering."""
        target_name = collection_name or self.collection_name
        target_size = vector_size or self.vector_size

        collections = client.get_collections().collections
        collection_exists = any(c.name == target_name for c in collections)

        if collection_exists and force_recreate:
            client.delete_collection(collection_name=target_name)
            collection_exists = False

        if not collection_exists:
            client.create_collection(
                collection_name=target_name,
                vectors_config=VectorParams(size=target_size, distance=Distance.COSINE),
            )

        try:
            client.create_payload_index(
                collection_name=target_name,
                field_name="doc_type",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=target_name,
                field_name="section",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=target_name,
                field_name="source_file",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass

    def ingest(self, force_recreate: bool = True) -> int:
        """Full ingestion pipeline for sample documentation."""
        client = self.get_client()
        self.create_or_recreate_collection(
            client, collection_name=self.collection_name, force_recreate=force_recreate
        )

        pdf_sections = self.parse_pdf(DATABASE_COMPARISON_PDF)
        md_sections = self.parse_markdown(ARCHITECTURE_GUIDELINES_MD)

        all_chunks_metadata: List[Dict[str, Any]] = []

        for sec in pdf_sections:
            chunks = self.chunk_text(
                sec["text"], chunk_size=self.chunk_size, overlap=self.chunk_overlap
            )
            for i, chunk in enumerate(chunks):
                all_chunks_metadata.append(
                    {
                        "content": chunk,
                        "source_file": sec["source_file"],
                        "doc_type": sec["doc_type"],
                        "section": sec["section"],
                        "chunk_index": i,
                        "page": sec.get("page", 1),
                    }
                )

        for sec in md_sections:
            chunks = self.chunk_text(
                sec["text"], chunk_size=self.chunk_size, overlap=self.chunk_overlap
            )
            for i, chunk in enumerate(chunks):
                all_chunks_metadata.append(
                    {
                        "content": chunk,
                        "source_file": sec["source_file"],
                        "doc_type": sec["doc_type"],
                        "section": sec["section"],
                        "chunk_index": i,
                    }
                )

        if not all_chunks_metadata:
            return 0

        model = self.get_embedding_model()
        texts_to_embed = [item["content"] for item in all_chunks_metadata]
        embeddings_generator = model.embed(texts_to_embed)
        embeddings = [e.tolist() for e in embeddings_generator]

        points: List[PointStruct] = []
        for i, (meta, vector) in enumerate(zip(all_chunks_metadata, embeddings)):
            unique_key = (
                f"{meta['source_file']}_{meta['section']}_{meta['chunk_index']}_{i}"
            )
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_key))
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=meta,
                )
            )

        client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        info = client.get_collection(collection_name=self.collection_name)
        total_indexed = info.points_count or len(points)
        return total_indexed

    def search(
        self,
        query: str,
        query_filter: Optional[Filter] = None,
        limit: int = 5,
        client: Optional[QdrantClient] = None,
    ) -> List[ScoredPoint]:
        """Search indexed documents using cosine similarity with optional metadata filter."""
        cli = client if client is not None else self.get_client()
        model = self.get_embedding_model()
        query_vector = list(model.embed([query]))[0].tolist()

        response = cli.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        )
        return response.points

    async def asearch(
        self,
        query: str,
        query_filter: Optional[Filter] = None,
        limit: int = 5,
        client: Optional[QdrantClient] = None,
    ) -> List[ScoredPoint]:
        """Search indexed documents asynchronously in a worker thread without blocking event loop."""
        import asyncio

        return await asyncio.to_thread(self.search, query, query_filter, limit, client)

    async def aingest(
        self,
        client: Optional[QdrantClient] = None,
        pdf_path: Optional[Path] = None,
        md_path: Optional[Path] = None,
    ) -> int:
        """Run document ingestion in a worker thread without blocking event loop."""
        import asyncio

        return await asyncio.to_thread(self.ingest, client, pdf_path, md_path)


# Default singleton instance
default_qdrant_ingestor = QdrantDocumentIngestor()

# Backwards compatibility function aliases
get_embedding_model = default_qdrant_ingestor.get_embedding_model
get_qdrant_client = default_qdrant_ingestor.get_client
chunk_text = default_qdrant_ingestor.chunk_text
parse_pdf = default_qdrant_ingestor.parse_pdf
parse_markdown = default_qdrant_ingestor.parse_markdown
create_or_recreate_collection = default_qdrant_ingestor.create_or_recreate_collection
ingest_all_documents = default_qdrant_ingestor.ingest
search_documents = default_qdrant_ingestor.search
asearch_documents = default_qdrant_ingestor.asearch
aingest_all_documents = default_qdrant_ingestor.aingest

if __name__ == "__main__":
    ingest_all_documents(force_recreate=True)
