"""FastAPI application for AI Research & Report Generation Agent."""

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from routes import api_router
    from services import (
        HumanReviewRequest,
        ResearchStartRequest,
        initialize_auth,
    )
except ImportError:
    from src.routes import api_router  # type: ignore
    from src.services import (  # type: ignore
        HumanReviewRequest,
        ResearchStartRequest,
        initialize_auth,
    )

# Initialize authentication persistence and demo credentials
initialize_auth()

# Setup FastAPI App
app = FastAPI(
    title="AI Research & Report Generation Agent",
    description="Agentic technical research, deterministic data analysis, human-in-the-loop review, and publication export.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def api_root() -> Dict[str, Any]:
    """API Root endpoint for the AI Research & Report Generation Agent backend."""
    return {
        "service": "AI Technical Research & Decision Report Agent API",
        "version": "2.0",
        "status": "healthy",
        "docs_url": "/docs",
        "frontend_url": "http://localhost:3000",
    }


# Mount modular routes
app.include_router(api_router)

__all__ = ["HumanReviewRequest", "ResearchStartRequest", "app"]
