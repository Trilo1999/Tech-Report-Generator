"""Authentication and user management routes."""

from typing import List

from fastapi import APIRouter, Depends

from services.auth_service import (
    list_demo_accounts,
    login_account,
    register_account,
)
from src.server.auth import (
    DemoUserPublic,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    User,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest) -> TokenResponse:
    """Register a new user account and return JWT credentials."""
    return register_account(request)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Verify email and password credentials, returning JWT access token."""
    return login_account(request)


@router.get("/me", response_model=User)
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> User:
    """Retrieve profile and role information for currently authenticated user."""
    return current_user


@router.get("/demo-users", response_model=List[DemoUserPublic])
async def list_demo_users() -> List[DemoUserPublic]:
    """Retrieve pre-configured demo credentials for instantaneous UI role testing."""
    return list_demo_accounts()
