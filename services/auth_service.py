"""Authentication and user management service."""

from typing import List

from fastapi import HTTPException

from src.server.auth import (
    DEMO_ACCOUNTS,
    DemoUserPublic,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    User,
    create_access_token,
    create_user,
    get_user_by_email,
    init_auth_db,
    verify_password,
)


def initialize_auth() -> None:
    """Initialize database tables and seed demo accounts if necessary."""
    init_auth_db()


def register_account(request: RegisterRequest) -> TokenResponse:
    """Register a new user account and return JWT credentials."""
    role = request.role if request.role in ["researcher", "reviewer", "viewer"] else "researcher"
    user = create_user(
        email=request.email,
        name=request.name,
        password=request.password,
        role=role,
    )
    token = create_access_token(user)
    return TokenResponse(access_token=token, user=user)


def login_account(request: LoginRequest) -> TokenResponse:
    """Verify email and password credentials, returning JWT access token."""
    user_db = get_user_by_email(request.email)
    if not user_db or not verify_password(request.password, user_db.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = User(
        id=user_db.id,
        email=user_db.email,
        name=user_db.name,
        role=user_db.role,
        created_at=user_db.created_at,
    )
    token = create_access_token(user)
    return TokenResponse(access_token=token, user=user)


def list_demo_accounts() -> List[DemoUserPublic]:
    """Retrieve pre-configured demo credentials for instantaneous UI role testing."""
    return [DemoUserPublic(**acc) for acc in DEMO_ACCOUNTS]
