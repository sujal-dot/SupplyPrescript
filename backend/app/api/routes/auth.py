"""
SupplyPrescript — Authentication API Router (Day 24 Security)
==============================================================
Endpoints for user login, token issuance, token verification, and user profile retrieval.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import (
    DEFAULT_SYSTEM_USERS,
    ROLE_PERMISSIONS,
    Role,
    create_access_token,
    get_current_user,
    hash_password,
    seed_default_users_if_needed,
    verify_password,
)
from app.core.config import settings
from app.database.connection import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserProfileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue JWT Access Token (Login)",
    description="Authenticates username and password against database bcrypt hashes and issues signed HS256 JWT.",
)
@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticates credentials and returns access token."""
    username = request.username.strip()
    password = request.password

    # Auto-seed default users if table is empty
    seed_default_users_if_needed(db)

    # 1. Lookup User in Database
    user = (
        db.query(User)
        .filter((User.username == username) | (User.email == username))
        .first()
    )

    valid_auth = False
    if user and user.hashed_password:
        valid_auth = verify_password(password, user.hashed_password)
    else:
        # Fallback check against default credentials if DB record was not found
        for default_user in DEFAULT_SYSTEM_USERS:
            if default_user["username"] == username or default_user["email"] == username:
                if password == default_user["password"]:
                    valid_auth = True
                    # Persist user to database for future queries
                    user = User(
                        user_id=default_user["user_id"],
                        username=default_user["username"],
                        email=default_user["email"],
                        hashed_password=hash_password(default_user["password"]),
                        full_name=default_user["full_name"],
                        role=default_user["role"],
                        is_active=True,
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                break

    if not valid_auth or not user:
        logger.warning("Failed login attempt for username: %s", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning("Login attempted for disabled account: %s", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated. Contact an administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Issue Signed JWT Access Token
    user_role = (user.role or Role.OPERATOR.value).upper()
    permissions = ROLE_PERMISSIONS.get(user_role, [])
    token_payload = {
        "sub": user.username,
        "user_id": user.user_id,
        "role": user_role,
        "email": user.email,
        "full_name": user.full_name,
    }
    access_token = create_access_token(data=token_payload)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    logger.info("Successfully issued JWT access token for user '%s' (role: %s)", user.username, user_role)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user_id=user.user_id,
        username=user.username,
        role=user_role,
        permissions=permissions,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Authenticated User Profile",
    description="Returns current authenticated user profile, active role, and system permissions.",
)
def get_user_profile(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Returns profile details of the acting authenticated user."""
    role = (current_user.role or Role.OPERATOR.value).upper()
    permissions = ROLE_PERMISSIONS.get(role, [])
    return UserProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=role,
        permissions=permissions,
        is_active=current_user.is_active,
    )
