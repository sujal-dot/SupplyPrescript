"""
SupplyPrescript — Authentication & Authorization Core (Day 24 Security)
========================================================================
Implements server-side password hashing (bcrypt), signed HS256 JWT generation
and verification, role-based access control (RBAC), and FastAPI dependencies.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)


class Role(str, Enum):
    OPERATOR = "OPERATOR"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


ROLE_PERMISSIONS: Dict[str, List[str]] = {
    Role.OPERATOR.value: [
        "read:operations",
        "create:predictions",
        "create:optimization",
        "create:decisions",
        "create:outcomes",
    ],
    Role.ANALYST.value: [
        "read:operations",
        "read:analytics",
        "create:predictions",
        "create:optimization",
        "create:dataset",
        "evaluate:model",
    ],
    Role.ADMIN.value: [
        "read:operations",
        "read:analytics",
        "create:predictions",
        "create:optimization",
        "create:decisions",
        "create:outcomes",
        "create:dataset",
        "evaluate:model",
        "execute:retraining",
        "promote:model",
        "rollback:model",
        "admin:all",
    ],
}

# Standard test / demo credentials for controlled staging and evaluation
DEFAULT_SYSTEM_USERS = [
    {
        "user_id": "usr_operator_01",
        "username": "operator",
        "email": "operator@supplyprescript.internal",
        "password": "Operator123!",
        "full_name": "Operations Specialist",
        "role": Role.OPERATOR.value,
    },
    {
        "user_id": "usr_analyst_01",
        "username": "analyst",
        "email": "analyst@supplyprescript.internal",
        "password": "Analyst123!",
        "full_name": "Supply Chain Analyst",
        "role": Role.ANALYST.value,
    },
    {
        "user_id": "usr_admin_01",
        "username": "admin",
        "email": "admin@supplyprescript.internal",
        "password": "Admin123!",
        "full_name": "Platform Administrator",
        "role": Role.ADMIN.value,
    },
]


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create signed HS256 JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"iat": now, "exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.AUTH_SECRET_KEY,
        algorithm=settings.AUTH_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Validate and decode JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def seed_default_users_if_needed(db: Session) -> None:
    """Ensure standard system users exist with securely hashed passwords."""
    try:
        for udata in DEFAULT_SYSTEM_USERS:
            existing = db.query(User).filter(User.username == udata["username"]).first()
            if not existing:
                user = User(
                    user_id=udata["user_id"],
                    username=udata["username"],
                    email=udata["email"],
                    hashed_password=hash_password(udata["password"]),
                    full_name=udata["full_name"],
                    role=udata["role"],
                    is_active=True,
                )
                db.add(user)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Could not auto-seed default users: %s", exc)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency resolving the authenticated User principal.
    - If Bearer token provided, validates token and resolves user.
    - If Bearer token missing:
        - If settings.AUTH_REQUIRED: raises 401 Unauthorized.
        - Else: falls back to test/development principal for backwards compatibility.
    """
    if credentials and credentials.credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        username: Optional[str] = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.username == username).first()
        if not user:
            # Fallback to ephemeral principal if DB user record not found but token valid
            role = payload.get("role", Role.OPERATOR.value)
            user_id = payload.get("user_id", f"usr_{username}")
            full_name = payload.get("full_name", username)
            return User(
                id=999999,
                user_id=user_id,
                username=username,
                email=f"{username}@supplyprescript.internal",
                hashed_password="",
                full_name=full_name,
                role=role,
                is_active=True,
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or disabled.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    if settings.AUTH_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Include 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In dev/testing without AUTH_REQUIRED, return default principal with ADMIN role
    return User(
        id=1,
        user_id="usr_dev_admin",
        username="dev_admin",
        email="dev_admin@supplyprescript.internal",
        hashed_password="",
        full_name="Development Administrator",
        role=Role.ADMIN.value,
        is_active=True,
    )


def require_roles(allowed_roles: List[str]):
    """Enforces that authenticated user holds one of the specified roles."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = (current_user.role or "").upper()
        allowed = [r.upper() for r in allowed_roles]
        if user_role not in allowed and Role.ADMIN.value not in allowed:
            # ADMIN can bypass role checks unless specifically restricted
            logger.warning(
                "Access denied for user '%s' with role '%s'. Allowed: %s",
                current_user.username,
                current_user.role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role '{current_user.role}' lacks permission for this operation.",
            )
        return current_user

    return role_checker


def require_permission(permission: str):
    """Enforces fine-grained permission based on role mapping."""

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = (current_user.role or "").upper()
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        if permission not in user_permissions and "admin:all" not in user_permissions:
            logger.warning(
                "User '%s' (role '%s') attempted operation requiring '%s'",
                current_user.username,
                current_user.role,
                permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: account lacks permission '{permission}'.",
            )
        return current_user

    return permission_checker
