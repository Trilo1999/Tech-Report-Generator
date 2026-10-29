"""
Qdrant Document Ingestion Pipeline & Metadata Indexing.

Parses database_comparison.pdf and architecture_guidelines.md, applies context-aware
sliding-window chunking, generates 384-dimensional dense vectors with all-MiniLM-L6-v2,
and indexes them into Qdrant with searchable metadata payloads.
"""

from pathlib import Path
import re
import uuid
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

from src.config import (
    ARCHITECTURE_GUIDELINES_MD,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATABASE_COMPARISON_PDF,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_NAME,
    QDRANT_COLLECTION_NAME,
    QDRANT_PREFER_EMBEDDED,
    QDRANT_STORAGE_DIR,
    QDRANT_URL,
)

# Cached embedding model & Qdrant client singletons
_EMBEDDING_MODEL: Optional[TextEmbedding] = None
_QDRANT_CLIENT: Optional[QdrantClient] = None


def get_embedding_model() -> TextEmbedding:
    """Return a singleton instance of the FastEmbed model (all-MiniLM-L6-v2)."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        model_name = f"sentence-transformers/{EMBEDDING_MODEL_NAME}"
        _EMBEDDING_MODEL = TextEmbedding(model_name=model_name)
    return _EMBEDDING_MODEL


def get_qdrant_client(reconnect: bool = False) -> QdrantClient:
    """
    Connect to Qdrant with dual-mode flexibility:
    1. Try Docker container / remote URL (default: http://localhost:6333)
    2. Fall back to local embedded storage if unreachable or explicitly requested.
    Reuses an active client singleton to avoid file lock collisions in embedded mode.
    """
    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is not None and not reconnect:
        return _QDRANT_CLIENT

    if not QDRANT_PREFER_EMBEDDED:
        try:
            client = QdrantClient(url=QDRANT_URL, timeout=3.0, check_compatibility=False)
            # Verify connectivity
            client.get_collections()
            _QDRANT_CLIENT = client
            return _QDRANT_CLIENT
        except Exception:
            pass

    # Embedded storage fallback (singleton prevents portalocker collision)
    QDRANT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    _QDRANT_CLIENT = QdrantClient(path=str(QDRANT_STORAGE_DIR), check_compatibility=False)
    return _QDRANT_CLIENT


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping windows.
    Guarantees no critical phrase is cut in half without context in the neighboring chunk.
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(cleaned):
        end = start + chunk_size
        chunk = cleaned[start:end].strip()
        if len(chunk) >= 40:  # Ignore tiny trailing fragments
            chunks.append(chunk)
        start += step

    return chunks


def parse_pdf(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text page-by-page from a PDF, identifying section headings and chunking.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    reader = PdfReader(str(file_path))
    extracted_sections: List[Dict[str, Any]] = []

    # Regex for detecting numbered headings like "1. Introduction", "2. Data Model", "2.1 PostgreSQL"
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
                # Flush previous section if it has text
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
                    sub_name = sub_match.group(1).strip()
                    current_section = (
                        f"{parent_section} - {sub_name}" if parent_section != "General Overview" else sub_name
                    )
            else:
                current_text.append(line_str)

    # Flush final section
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


def parse_markdown(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract sections from markdown file using '## ' headers as natural semantic boundaries.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    extracted_sections: List[Dict[str, Any]] = []
    current_section = "Overview & Scope"
    current_text: List[str] = []

    for line in lines:
        if line.startswith("## "):
            # Flush previous section
            if current_text:
                body = "\n".join(current_text).strip()
                if body:
                    extracted_sections.append(
                        {
                            "section": current_section,
                            "text": body,
                            "source_file": file_path.name,
                            "doc_type": "guideline",
                        }
                    )
                current_text = []
            current_section = line.replace("##", "").strip()
        elif line.startswith("# ") and not current_text:
            current_section = line.replace("#", "").strip()
        else:
            current_text.append(line)

    # Flush final section
    if current_text:
        body = "\n".join(current_text).strip()
        if body:
            extracted_sections.append(
                {
                    "section": current_section,
                    "text": body,
                    "source_file": file_path.name,
                    "doc_type": "guideline",
                }
            )

    return extracted_sections


def create_or_recreate_collection(
    client: QdrantClient,
    collection_name: str = QDRANT_COLLECTION_NAME,
    vector_size: int = EMBEDDING_DIMENSION,
    force_recreate: bool = True,
) -> None:
    """
    Initialize collection with Cosine distance and create payload indexes for fast filtering.
    """
    collections = client.get_collections().collections
    collection_exists = any(c.name == collection_name for c in collections)

    if collection_exists and force_recreate:
        client.delete_collection(collection_name=collection_name)
        collection_exists = False

    if not collection_exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    # Create keyword payload indexes for metadata filtering
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="doc_type",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="section",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="source_file",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception:
        # Ignore if index already exists
        pass


def ingest_all_documents(force_recreate: bool = True) -> int:
    """
    Full ingestion pipeline:
    1. Parse database_comparison.pdf and architecture_guidelines.md
    2. Slice into context-preserving overlapping chunks
    3. Generate 384-dim dense embeddings
    4. Upsert with deterministic UUIDs and rich metadata payloads
    5. Return the total count of indexed vector points.
    """
    client = get_qdrant_client()
    create_or_recreate_collection(client, collection_name=QDRANT_COLLECTION_NAME, force_recreate=force_recreate)

    # Step 1: Parse both files into sections
    pdf_sections = parse_pdf(DATABASE_COMPARISON_PDF)
    md_sections = parse_markdown(ARCHITECTURE_GUIDELINES_MD)

    all_chunks_metadata: List[Dict[str, Any]] = []

    # Step 2: Chunk PDF sections
    for sec in pdf_sections:
        chunks = chunk_text(sec["text"], chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
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

    # Step 2b: Chunk Markdown sections
    for sec in md_sections:
        chunks = chunk_text(sec["text"], chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
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

    # Step 3: Generate dense vector embeddings
    model = get_embedding_model()
    texts_to_embed = [item["content"] for item in all_chunks_metadata]
    embeddings_generator = model.embed(texts_to_embed)
    embeddings = [e.tolist() for e in embeddings_generator]

    # Step 4: Build deterministic PointStruct objects (UUID5 based on content and location)
    points: List[PointStruct] = []
    for i, (meta, vector) in enumerate(zip(all_chunks_metadata, embeddings)):
        unique_key = f"{meta['source_file']}_{meta['section']}_{meta['chunk_index']}_{i}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_key))

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload=meta,
            )
        )

    # Step 5: Upsert points in batch
    client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=points,
    )

    info = client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
    total_indexed = info.points_count or len(points)

    print("✅ Ingestion Complete!")
    print(f"   Collection: '{QDRANT_COLLECTION_NAME}'")
    print(f"   Total points indexed: {total_indexed}")
    print(f"   PDF chunks: {sum(1 for m in all_chunks_metadata if m['doc_type'] == 'pdf')}")
    print(f"   Guideline chunks: {sum(1 for m in all_chunks_metadata if m['doc_type'] == 'guideline')}")

    return total_indexed


def search_documents(
    query: str,
    query_filter: Optional[Filter] = None,
    limit: int = 5,
    client: Optional[QdrantClient] = None,
) -> List[ScoredPoint]:
    """
    Search indexed documents using cosine similarity with optional metadata filter.
    Returns list of ScoredPoint with payload.
    """
    if client is None:
        client = get_qdrant_client()

    model = get_embedding_model()
    query_vector = list(model.embed([query]))[0].tolist()

    response = client.query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
    )
    return response.points


if __name__ == "__main__":
    ingest_all_documents(force_recreate=True)
