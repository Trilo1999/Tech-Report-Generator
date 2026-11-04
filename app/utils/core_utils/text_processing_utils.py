import os
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.log_config import logger
from app.constants.app_constants import ALLOWED_FILES, VECTOR_DB


class TextProcessor:
    """Load and split documents into chunks."""

    def __init__(
        self,
        file_path: str,
        chunk_size: int = VECTOR_DB.CHUNK_SIZE.value,
        chunk_overlap: int = VECTOR_DB.CHUNK_OVERLAP.value,
    ) -> None:
        """Initialize text processor for a file.

        Args:
            file_path: Path to the document file.
            chunk_size: Size of each text chunk. Defaults to VECTOR_DB setting.
            chunk_overlap: Overlap between chunks. Defaults to VECTOR_DB setting.
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_documents(self):
        """Load documents from the file based on extension.

        Returns:
            List of loaded Document objects.

        Raises:
            ValueError: If file extension is unsupported.
        """
        file_extension = os.path.splitext(self.file_path)[1].lower()

        try:
            if file_extension == ALLOWED_FILES.PDF.value:
                loader = PyPDFLoader(self.file_path)
            else:
                raise ValueError("Invalid file extension")
            return loader.load()
        except Exception:
            logger.exception("Failed to load documents from %s", self.file_path)
            raise

    def split_documents(self, docs) -> List:
        """Split documents into chunks.

        Args:
            docs: List of documents loaded from the file to split.

        Returns:
            List of document chunks.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        return text_splitter.split_documents(docs)

    def process(self) -> List:
        """Load and split documents in one step.

        Returns:
            List of document chunks ready for indexing.
        """
        docs = self.load_documents()
        return self.split_documents(docs)


def sanitize_topic(raw_topic: str) -> str:
    """
    Clean, sanitize, and professionally format user research topic prompts.
    Strips conversational preambles (e.g. 'give me a report about ...'), fixes common typos,
    and returns a clean, capitalized title suitable for reports and databases.
    """
    if not raw_topic or not raw_topic.strip():
        return "Technical Architecture Evaluation"

    import re

    t = raw_topic.strip().strip("\"'").strip()

    # Strip conversational prompt prefixes
    patterns = [
        r"^(?:please\s+)?(?:can\s+you\s+)?(?:give\s+me\s+a\s+|provide\s+(?:me\s+)?(?:a\s+)?|write\s+a\s+|generate\s+a\s+|create\s+a\s+|draft\s+a\s+|build\s+a\s+|prepare\s+a\s+)?(?:detailed\s+|comprehensive\s+|technical\s+)?(?:research\s+)?(?:report|analysis|evaluation|comparison|study|document|overview)\s+(?:about|on|for|of|regarding)\s+",
        r"^(?:please\s+)?(?:can\s+you\s+)?(?:tell\s+me\s+about|research\s+about|research\s+on|research\s+into|investigate)\s+",
        r"^(?:please\s+)?(?:can\s+you\s+)?(?:give\s+me\s+an?\s+overview\s+of)\s+",
    ]
    for p in patterns:
        t = re.sub(p, "", t, flags=re.IGNORECASE).strip()

    # Strip trailing punctuation
    t = re.sub(r"[\?\.\!\;\,]+$", "", t).strip()

    # Common typo fixes and term normalizations
    substitutions = [
        (r"\bpatform\b", "platform"),
        (r"\becommerce\b", "e-commerce"),
        (r"\be-comerce\b", "e-commerce"),
        (r"\bmultitenant\b", "multi-tenant"),
        (r"\bmulti tenant\b", "multi-tenant"),
        (r"\bsaas[- ]based\b", "SaaS-based"),
    ]
    for pattern, repl in substitutions:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # Word capitalization preserving acronyms and hyphenated terms
    words = t.split()
    minor_words = {
        "a",
        "an",
        "the",
        "and",
        "but",
        "or",
        "for",
        "nor",
        "on",
        "at",
        "to",
        "by",
        "over",
        "in",
        "with",
        "vs",
        "versus",
    }
    acronyms = {
        "saas": "SaaS",
        "api": "API",
        "aws": "AWS",
        "gcp": "GCP",
        "rls": "RLS",
        "tco": "TCO",
        "sql": "SQL",
        "nosql": "NoSQL",
        "llm": "LLM",
        "ai": "AI",
        "rag": "RAG",
        "db": "DB",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mongodb": "MongoDB",
    }

    capitalized = []
    for idx, w in enumerate(words):
        w_lower = w.lower()
        if w_lower in acronyms:
            capitalized.append(acronyms[w_lower])
        elif "-" in w:
            parts = [acronyms.get(p.lower(), p.capitalize()) for p in w.split("-")]
            capitalized.append("-".join(parts))
        elif idx > 0 and w_lower in minor_words:
            capitalized.append(w_lower)
        else:
            capitalized.append(w.capitalize())

    sanitized = " ".join(capitalized)
    return sanitized or "Technical Architecture Evaluation"
