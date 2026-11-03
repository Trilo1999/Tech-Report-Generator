"""Report file generation and download service implementing OOP patterns."""

from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.agents.graph.checkpoints import get_thread_state
from app.exceptions.domain import NotFoundError
from app.services.iam_services.research_auth import decode_access_token, get_user_by_id


class ReportService:
    """Service class managing report generation, format transformations, and file streaming."""

    @classmethod
    def download_report(
        cls,
        thread_id: str,
        format: str = "pdf",
        token: Optional[str] = None,
        auth_credentials: Optional[HTTPAuthorizationCredentials] = None,
    ) -> FileResponse:
        """Download the final exported report in PDF or Microsoft Word (.docx) format."""
        raw_token = auth_credentials.credentials if (auth_credentials and auth_credentials.credentials) else token
        if not raw_token:
            raise HTTPException(
                status_code=401,
                detail="Authentication token required to download report.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = decode_access_token(raw_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid or expired token: {str(exc)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user = get_user_by_id(payload.get("sub", ""))
        if not user:
            raise HTTPException(status_code=401, detail="User account not found.")

        snapshot = get_thread_state(thread_id)
        if not snapshot:
            raise NotFoundError(f"Thread '{thread_id}' not found.")

        report_path_str = snapshot["values"].get("final_report_path")
        if not report_path_str:
            raise HTTPException(
                status_code=400, detail="No exported report found. The proposal must be approved first."
            )

        report_path = Path(report_path_str)
        if not report_path.is_file():
            raise NotFoundError("Exported report file not found on disk.")

        target_format = format.lower().strip()
        if target_format in ("docx", "doc", "word"):
            docx_path = report_path.with_suffix(".docx")
            if not docx_path.is_file():
                from app.tools.report_exporter_tool import generate_report

                values = snapshot["values"]
                draft = values.get("draft_report") or {}
                content = {
                    "title": draft.get("title", f"Report: {values.get('topic')}"),
                    "sections": draft.get("sections", {}),
                    "cited_sources": draft.get("cited_sources", []),
                    "evidence_items": values.get("evidence", []),
                    "unsupported_claims": values.get("unsupported_claims", []),
                    "metadata": {"topic": values.get("topic")},
                }
                docx_path = Path(generate_report(content, format="docx"))

            return FileResponse(
                path=str(docx_path),
                filename=docx_path.name,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        return FileResponse(
            path=str(report_path),
            filename=report_path.name,
            media_type="application/pdf",
        )


# Backwards compatibility function alias
download_report_file = ReportService.download_report
