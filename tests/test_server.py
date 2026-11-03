"""
Unit and integration tests for FastAPI REST Endpoints and Review Dashboard.
"""

from fastapi.testclient import TestClient

from src.server.app import app

client = TestClient(app)


def get_token_for(email: str, password: str) -> str:
    """Helper to authenticate and retrieve access token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_api_root():
    """Verify GET / returns API root information and health status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "AI Technical Research & Decision Report Agent API" in data["service"]


def test_api_research_workflow_lifecycle():
    """Verify full REST workflow lifecycle: start -> status -> revision -> approval -> download."""
    researcher_token = get_token_for("researcher@antigravity.ai", "Research@123")
    reviewer_token = get_token_for("reviewer@antigravity.ai", "Reviewer@123")
    viewer_token = get_token_for("viewer@antigravity.ai", "Viewer@123")

    researcher_headers = {"Authorization": f"Bearer {researcher_token}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # 1. Start research workflow (as Researcher)
    start_payload = {"topic": "Enterprise Persistence Architecture Decision", "sync": True}
    start_res = client.post("/api/research/start", json=start_payload, headers=researcher_headers)
    assert start_res.status_code == 200
    start_data = start_res.json()

    thread_id = start_data["thread_id"]
    assert thread_id.startswith("research_")
    assert start_data["status"] == "drafted"
    assert start_data["is_pending_review"] is True
    assert "draft_report" in start_data

    # 2. Query status (as Viewer)
    status_res = client.get(f"/api/research/status/{thread_id}", headers=viewer_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["topic"] == "Enterprise Persistence Architecture Decision"
    assert len(status_data["subquestions"]) >= 3
    assert len(status_data["evidence"]) >= 3
    assert status_data["is_pending_review"] is True

    # 3. Submit revision review (as Researcher requesting target section revision)
    revision_payload = {
        "decision": "revise",
        "feedback_notes": "Incorporate 36-month reserved instance economics.",
        "target_sections": ["TCO & Cloud Cost Projection"],
        "sync": True,
    }
    rev_res = client.post(f"/api/research/review/{thread_id}", json=revision_payload, headers=researcher_headers)
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    sections = rev_data["draft_report"]["sections"]
    assert "36-month" in sections["TCO & Cloud Cost Projection"]
    assert rev_data["is_pending_review"] is True

    # 4. Submit final approval (as Reviewer)
    approve_payload = {
        "decision": "approved",
        "feedback_notes": "Architecture validated.",
        "target_sections": [],
        "sync": True,
    }
    appr_res = client.post(f"/api/research/review/{thread_id}", json=approve_payload, headers=reviewer_headers)
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "completed"
    assert appr_data["final_report_path"] is not None

    # 5. Download generated publication PDF (as Viewer)
    dl_res = client.get(f"/api/research/download/{thread_id}", headers=viewer_headers)
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 500

    # 6. Download generated Word document (.docx)
    dl_docx_res = client.get(f"/api/research/download/{thread_id}?format=docx", headers=viewer_headers)
    assert dl_docx_res.status_code == 200
    assert "wordprocessingml" in dl_docx_res.headers["content-type"]
    assert len(dl_docx_res.content) > 500


def test_api_research_not_found():
    """Verify 404 response for non-existent thread."""
    token = get_token_for("viewer@antigravity.ai", "Viewer@123")
    response = client.get("/api/research/status/non_existent_thread_xyz", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_api_async_background_task_and_polling():
    """Verify task-based asynchronous dispatch returns immediately with status=running."""
    token = get_token_for("researcher@antigravity.ai", "Research@123")
    headers = {"Authorization": f"Bearer {token}"}

    # Dispatch task asynchronously (sync=False default)
    payload = {"topic": "Asynchronous Background Task Architecture Benchmark"}
    res = client.post("/api/research/start", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "thread_id" in data
    assert data["status"] == "running"
    assert data["is_running"] is True
    assert "status_url" in data

    # Poll status immediately
    status_res = client.get(f"/api/research/status/{data['thread_id']}", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["thread_id"] == data["thread_id"]
    assert "is_running" in status_data


def test_api_user_specific_research_tasks_and_tracking():
    """Verify that research tasks are tracked per user and can be listed and deleted."""
    researcher_token = get_token_for("researcher@antigravity.ai", "Research@123")
    viewer_token = get_token_for("viewer@antigravity.ai", "Viewer@123")

    r_headers = {"Authorization": f"Bearer {researcher_token}"}
    v_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Researcher creates a task
    res = client.post(
        "/api/research/start",
        json={"topic": "React vs Angular Performance Comparison", "sync": True},
        headers=r_headers,
    )
    assert res.status_code == 200
    created = res.json()
    thread_id = created["thread_id"]

    # Researcher lists tasks - should include the new task
    tasks_res = client.get("/api/research/tasks", headers=r_headers)
    assert tasks_res.status_code == 200
    tasks = tasks_res.json()
    assert any(t["thread_id"] == thread_id for t in tasks)

    # Viewer lists tasks - should NOT include researcher's task
    viewer_tasks_res = client.get("/api/research/tasks", headers=v_headers)
    assert viewer_tasks_res.status_code == 200
    viewer_tasks = viewer_tasks_res.json()
    assert not any(t["thread_id"] == thread_id for t in viewer_tasks)

    # Researcher deletes the task
    del_res = client.delete(f"/api/research/tasks/{thread_id}", headers=r_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Listing again should not contain deleted task
    tasks_res2 = client.get("/api/research/tasks", headers=r_headers)
    assert tasks_res2.status_code == 200
    assert not any(t["thread_id"] == thread_id for t in tasks_res2.json())
