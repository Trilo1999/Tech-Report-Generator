"""
Unit and integration tests for Authentication and Role-Based Access Control (RBAC).
"""

import time
from fastapi.testclient import TestClient

from app.main import app
from app.services.iam_services.research_auth import hash_password, verify_password

client = TestClient(app)


def test_password_hashing_and_verification():
    """Verify password hashing with salt and PBKDF2 comparison."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert "$" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_list_demo_users():
    """Verify demo accounts endpoint lists all 4 predefined roles."""
    res = client.get("/api/auth/demo-users")
    assert res.status_code == 200
    demos = res.json()
    assert len(demos) == 4
    roles = {d["role"] for d in demos}
    assert roles == {"admin", "researcher", "reviewer", "viewer"}


def test_login_demo_accounts():
    """Verify authentication for pre-seeded demo accounts."""
    for email, pw in [
        ("admin@antigravity.ai", "Admin@123"),
        ("researcher@antigravity.ai", "Research@123"),
        ("reviewer@antigravity.ai", "Reviewer@123"),
        ("viewer@antigravity.ai", "Viewer@123"),
    ]:
        res = client.post("/api/auth/login", json={"email": email, "password": pw})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email


def test_login_invalid_credentials():
    """Verify 401 response for wrong password or non-existent user."""
    # Wrong password
    res = client.post("/api/auth/login", json={"email": "admin@antigravity.ai", "password": "BadPassword"})
    assert res.status_code == 401

    # Non-existent email
    res2 = client.post("/api/auth/login", json={"email": "nobody@antigravity.ai", "password": "Password123"})
    assert res2.status_code == 401


def test_register_and_get_me():
    """Verify user registration and profile extraction via Bearer token."""
    unique_email = f"user_{int(time.time() * 1000)}@antigravity.ai"
    reg_payload = {
        "email": unique_email,
        "name": "Jane Engineer",
        "password": "PasswordJane@123",
        "role": "researcher",
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    token = reg_data["access_token"]
    assert reg_data["user"]["name"] == "Jane Engineer"

    # Fetch profile
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == unique_email
    assert me_data["role"] == "researcher"


def test_duplicate_registration_rejected():
    """Verify duplicate email registration returns 400."""
    payload = {
        "email": "admin@antigravity.ai",
        "name": "Admin Clone",
        "password": "Password@123",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400


def test_unauthenticated_request_rejected():
    """Verify 401 when accessing protected endpoints without Authorization header."""
    res = client.post("/api/research/start", json={"topic": "Test Without Auth"})
    assert res.status_code == 401

    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 401


def test_invalid_token_rejected():
    """Verify 401 when accessing endpoints with malformed or invalid token."""
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.value"})
    assert res.status_code == 401


def test_rbac_restrictions_on_research_start():
    """Verify RBAC: Only 'admin' and 'researcher' can start research."""
    # Viewer token
    viewer_login = client.post("/api/auth/login", json={"email": "viewer@antigravity.ai", "password": "Viewer@123"})
    viewer_token = viewer_login.json()["access_token"]

    # Reviewer token
    reviewer_login = client.post(
        "/api/auth/login", json={"email": "reviewer@antigravity.ai", "password": "Reviewer@123"}
    )
    reviewer_token = reviewer_login.json()["access_token"]

    # Viewer attempt -> 403 Forbidden
    res_viewer = client.post(
        "/api/research/start",
        json={"topic": "Forbidden test"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_viewer.status_code == 403
    assert "Forbidden" in res_viewer.json()["detail"]

    # Reviewer attempt -> 403 Forbidden
    res_reviewer = client.post(
        "/api/research/start",
        json={"topic": "Forbidden test"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_reviewer.status_code == 403
    assert "Forbidden" in res_reviewer.json()["detail"]
