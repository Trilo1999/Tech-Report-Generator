"""Authentication and Role-Based Access Control (RBAC) service.

Provides PBKDF2 password hashing, RFC 7519 HMAC-SHA256 JWT tokens,
PostgreSQL persistence, and FastAPI dependency injectors for role authorization.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Literal, Optional
import uuid

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from src.config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY
from src.db.postgres import (
    init_postgres_schema,
    is_postgres_available,
    pg_create_user,
    pg_get_user_by_email,
    pg_get_user_by_id,
)

# Role definitions
RoleType = Literal["admin", "researcher", "reviewer", "viewer"]

# HTTP Bearer scheme (auto_error=False allows handling custom unauthorized responses)
bearer_scheme = HTTPBearer(auto_error=False)


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────
class User(BaseModel):
    id: str
    email: str
    name: str
    role: RoleType
    created_at: float


class UserInDB(User):
    password_hash: str


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=2, max_length=60)
    password: str = Field(..., min_length=6)
    role: Optional[RoleType] = Field("researcher", description="Assigned user role")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class DemoUserPublic(BaseModel):
    email: str
    name: str
    role: RoleType
    password: str
    description: str


# ──────────────────────────────────────────────
# Password Hashing & JWT Implementation
# ──────────────────────────────────────────────
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = uuid.uuid4().hex
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"{salt}${hashed}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Safely compare plain password against stored salt$hash."""
    try:
        salt, _ = stored_hash.split("$", 1)
        expected = hash_password(plain_password, salt=salt)
        return hmac.compare_digest(expected, stored_hash)
    except Exception:
        return False


def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_access_token(user: User, expires_delta_seconds: Optional[int] = None) -> str:
    """Generate RFC 7519 compliant HS256 JWT string."""
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64_url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    now = int(time.time())
    exp = now + (expires_delta_seconds if expires_delta_seconds is not None else (JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60))

    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "iat": now,
        "exp": exp,
    }
    encoded_payload = _b64_url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_sig = _b64_url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_sig}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify signature and expiration of JWT token."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format: token must contain 3 segments")

    encoded_header, encoded_payload, encoded_sig = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        actual_sig = _b64_url_decode(encoded_sig)
    except Exception as exc:
        raise ValueError("Invalid base64 signature in token") from exc

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid token signature")

    try:
        payload_bytes = _b64_url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Malformed token payload") from exc

    if "exp" in payload and time.time() > payload["exp"]:
        raise ValueError("Token has expired")

    return payload


# ──────────────────────────────────────────────
# SQLite Persistence & Seeding
# ──────────────────────────────────────────────
DEMO_ACCOUNTS = [
    {
        "email": "admin@antigravity.ai",
        "name": "System Administrator",
        "role": "admin",
        "password": "Admin@123",
        "description": "Full privileges: start research, revise, approve/reject reports, view state, manage system.",
    },
    {
        "email": "researcher@antigravity.ai",
        "name": "Lead Researcher",
        "role": "researcher",
        "password": "Research@123",
        "description": "Can trigger research workflows, view state, request section revisions, and download reports.",
    },
    {
        "email": "reviewer@antigravity.ai",
        "name": "Senior Reviewer",
        "role": "reviewer",
        "password": "Reviewer@123",
        "description": "Can inspect queued reports, submit review verdicts (approve, revise, reject), and download reports.",
    },
    {
        "email": "viewer@antigravity.ai",
        "name": "Stakeholder Viewer",
        "role": "viewer",
        "password": "Viewer@123",
        "description": "Read-only access: can view research state, monitor progress, and download completed reports.",
    },
]


def init_auth_db() -> None:
    """Initialize PostgreSQL users schema and seed demo accounts."""
    if is_postgres_available():
        demo_accounts_prepared = [
            {
                "email": demo["email"],
                "name": demo["name"],
                "role": demo["role"],
                "password_hash": hash_password(demo["password"]),
            }
            for demo in DEMO_ACCOUNTS
        ]
        init_postgres_schema(demo_accounts_prepared)


def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Retrieve user by email directly from PostgreSQL."""
    clean_email = email.strip().lower()
    pg_user = pg_get_user_by_email(clean_email)
    if pg_user:
        return UserInDB(**pg_user)
    return None


def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Retrieve user by user id directly from PostgreSQL."""
    pg_user = pg_get_user_by_id(user_id)
    if pg_user:
        return UserInDB(**pg_user)
    return None


def create_user(email: str, name: str, password: str, role: RoleType = "researcher") -> User:
    """Create and persist a new user exclusively in PostgreSQL."""
    clean_email = email.strip().lower()
    clean_name = name.strip()

    # Reject if user already exists
    existing = get_user_by_email(clean_email)
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)
    now = time.time()

    user_dict = {
        "id": user_id,
        "email": clean_email,
        "name": clean_name,
        "role": role,
        "password_hash": pw_hash,
        "created_at": now,
    }

    try:
        success = pg_create_user(user_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to persist user in PostgreSQL.")
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err)) from val_err

    return User(id=user_id, email=clean_email, name=clean_name, role=role, created_at=now)


# ──────────────────────────────────────────────
# FastAPI Dependencies & RBAC Guards
# ──────────────────────────────────────────────
async def get_current_user_optional(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[User]:
    """Extract authenticated user if Authorization header is present."""
    if not auth_credentials or not auth_credentials.credentials:
        return None
    token = auth_credentials.credentials
    try:
        payload = decode_access_token(token)
    except ValueError:
        return None

    user = get_user_by_id(payload.get("sub", ""))
    if not user:
        return None
    return User(id=user.id, email=user.email, name=user.name, role=user.role, created_at=user.created_at)


async def get_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> User:
    """Enforce valid JWT authentication."""
    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_credentials.credentials
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(id=user.id, email=user.email, name=user.name, role=user.role, created_at=user.created_at)


def require_roles(allowed_roles: List[RoleType]):
    """Dependency factory enforcing RBAC permission checks."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: Action requires one of {allowed_roles} roles. "
                    f"Current user role: '{current_user.role}'."
                ),
            )
        return current_user

    return role_checker
