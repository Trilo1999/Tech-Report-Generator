"""
Unit and integration tests for FastAPI REST Endpoints and Review Dashboard.
"""

from fastapi.testclient import TestClient

from src.server.app import app

client = TestClient(app)


def test_serve_dashboard_html():
    """Verify GET / serves the interactive single-page HTML review dashboard."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AI Technical Research & Decision Report Agent" in response.text


def test_api_research_workflow_lifecycle():
    """Verify full REST workflow lifecycle: start -> status -> revision -> approval -> download."""
    # 1. Start research workflow
    start_payload = {"topic": "Enterprise Persistence Architecture Decision"}
    start_res = client.post("/api/research/start", json=start_payload)
    assert start_res.status_code == 200
    start_data = start_res.json()

    thread_id = start_data["thread_id"]
    assert thread_id.startswith("research_")
    assert start_data["status"] == "drafted"
    assert start_data["is_pending_review"] is True
    assert "draft_report" in start_data

    # 2. Query status
    status_res = client.get(f"/api/research/status/{thread_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["topic"] == "Enterprise Persistence Architecture Decision"
    assert len(status_data["subquestions"]) >= 3
    assert len(status_data["evidence"]) >= 3
    assert status_data["is_pending_review"] is True

    # 3. Submit revision review
    revision_payload = {
        "decision": "revise",
        "feedback_notes": "Incorporate 36-month reserved instance economics.",
        "target_sections": ["TCO & Cloud Cost Projection"],
    }
    rev_res = client.post(f"/api/research/review/{thread_id}", json=revision_payload)
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    sections = rev_data["draft_report"]["sections"]
    assert "36-month" in sections["TCO & Cloud Cost Projection"]
    assert rev_data["is_pending_review"] is True

    # 4. Submit final approval
    approve_payload = {
        "decision": "approved",
        "feedback_notes": "Architecture validated.",
        "target_sections": [],
    }
    appr_res = client.post(f"/api/research/review/{thread_id}", json=approve_payload)
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "completed"
    assert appr_data["final_report_path"] is not None

    # 5. Download generated publication PDF
    dl_res = client.get(f"/api/research/download/{thread_id}")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 500


def test_api_research_not_found():
    """Verify 404 response for non-existent thread."""
    response = client.get("/api/research/status/non_existent_thread_xyz")
    assert response.status_code == 404
