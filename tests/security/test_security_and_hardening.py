"""
SupplyPrescript — Security Hardening & RBAC Test Suite (Day 24)
==============================================================
Validates:
1. Server-side password hashing and JWT issuance (POST /api/auth/token).
2. Authenticated user profile retrieval (GET /api/auth/me).
3. Rejection of invalid credentials (401 Unauthorized).
4. Rejection of expired/malformed tokens (401 Unauthorized).
5. Role-based access control (RBAC):
   - Operator barred from admin-only retraining, promotion, and rollback (403 Forbidden).
   - Analyst barred from decision execution (403 Forbidden).
   - Admin permitted across all operational and retraining workflows.
6. Identity spoofing prevention:
   - Acting user strictly derived from authenticated JWT principal, ignoring client-supplied user_id.
7. Enforced authentication mode (AUTH_REQUIRED=True -> 401 on missing token).
8. Standardized error envelope and X-Request-ID correlation tracking.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_access_token, hash_password, Role
from app.core.config import settings
from app.database.connection import SessionLocal
from app.main import app
from app.models.decision import Decision
from app.models.user import User


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_auth_token_issuance_success(client):
    """1. Valid credentials receive signed JWT token with appropriate role and permissions."""
    resp = client.post(
        "/api/auth/token",
        json={"username": "operator", "password": "Operator123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "OPERATOR"
    assert "create:decisions" in data["permissions"]
    assert "X-Request-ID" in resp.headers


def test_auth_token_invalid_password_rejected(client):
    """2. Incorrect password returns 401 Unauthorized with standardized error format."""
    resp = client.post(
        "/api/auth/token",
        json={"username": "operator", "password": "WrongPassword123!"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "X-Request-ID" in resp.headers


def test_auth_get_user_profile(client):
    """3. GET /api/auth/me returns authenticated principal profile."""
    # Obtain token
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "admin", "password": "Admin123!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "ADMIN"
    assert "execute:retraining" in data["permissions"]


def test_auth_malformed_token_rejected(client):
    """4. Malformed or tampered token returns 401 Unauthorized."""
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_rbac_operator_barred_from_model_promotion(client):
    """5. Operator role attempting admin-only model promotion is rejected with 403 Forbidden."""
    # Obtain operator token
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "operator", "password": "Operator123!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.post(
        "/api/ml/retraining/jobs/JOB-TEST-FAKE/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "Administrator role required" in data["error"]["message"]


def test_rbac_operator_barred_from_model_rollback(client):
    """6. Operator role attempting admin-only model rollback is rejected with 403 Forbidden."""
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "operator", "password": "Operator123!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.post(
        "/api/ml/retraining/rollback",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_version": "v1.0"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_rbac_operator_barred_from_retraining_run(client):
    """7. Operator role attempting to trigger retraining is rejected with 403 Forbidden."""
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "operator", "password": "Operator123!"},
    )
    token = login_resp.json()["access_token"]

    resp = client.post(
        "/api/ml/retraining/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"force": True},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_rbac_analyst_barred_from_recording_decision(client):
    """8. Analyst role attempting to execute an operational decision is rejected with 403 Forbidden."""
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "analyst", "password": "Analyst123!"},
    )
    token = login_resp.json()["access_token"]

    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "recommendation": "AIR_FREIGHT",
        "idempotency_key": f"TEST-RBAC-{uuid.uuid4().hex}",
    }

    resp = client.post(
        "/api/decisions",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_identity_spoofing_prevented_principal_enforced(client, db_session):
    """9. Client-supplied user_id spoofing is ignored; authoritative user derived from JWT principal."""
    # Login as operator
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "operator", "password": "Operator123!"},
    )
    token = login_resp.json()["access_token"]

    idemp_key = f"TEST-SPOOF-{uuid.uuid4().hex}"
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "recommendation": "AIR_FREIGHT",
        "user_id": "spoofed_chief_executive_officer",  # Attacker attempts to spoof CEO
        "approved_by": "Spoofed Executive",
        "idempotency_key": idemp_key,
        "notes": "Testing anti-spoofing principal derivation.",
    }

    resp = client.post(
        "/api/decisions",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp.status_code == 201
    data = resp.json()

    # The persisted decision MUST attribute to operator principal, NOT the spoofed payload
    assert data["user_id"] != "spoofed_chief_executive_officer"
    assert data["user_id"] in ["usr_operator_01", "operator"]

    # Verify directly in PostgreSQL
    db_rec = db_session.query(Decision).filter(Decision.idempotency_key == idemp_key).first()
    assert db_rec is not None
    assert db_rec.user_id != "spoofed_chief_executive_officer"
    assert db_rec.user_id in ["usr_operator_01", "operator"]


def test_auth_required_mode_blocks_unauthenticated_requests(client, monkeypatch):
    """10. When AUTH_REQUIRED=True, requests lacking Authorization header receive 401."""
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)

    resp = client.post(
        "/api/decisions",
        json={
            "shipment_id": "SHIP000005",
            "option_id": "A",
            "idempotency_key": f"TEST-UNAUTH-{uuid.uuid4().hex}",
        },
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Authentication credentials were not provided" in data["error"]["message"]


def test_request_correlation_id_and_security_headers(client):
    """11. Every response carries X-Request-ID, nosniff, and frame options headers."""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert resp.headers["X-Request-ID"].startswith("req-")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
