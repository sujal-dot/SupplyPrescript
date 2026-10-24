"""
SupplyPrescript — Authentication Schemas (Day 24 Security)
===========================================================
Pydantic schemas for authentication requests, JWT token responses, and user profiles.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email address", min_length=2, max_length=64)
    password: str = Field(..., description="Plaintext user password", min_length=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifespan in seconds")
    user_id: str
    username: str
    role: str
    permissions: List[str]


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    permissions: List[str]
    is_active: bool
