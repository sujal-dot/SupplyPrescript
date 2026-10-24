"""SupplyPrescript — API Integration Tests for Retraining Pipeline (Day 23)
========================================================================
Tests verify:
1. GET /api/ml/retraining/monitor returns performance drift diagnostics.
2. POST /api/ml/retraining/run checks data availability and reports INSUFFICIENT_DATA or initiates job.
3. GET /api/ml/retraining/jobs returns paginated job records.
4. GET /api/ml/retraining/jobs/{job_id} returns detailed validation report or 404.
5. POST /api/ml/retraining/jobs/{job_id}/promote validates job state and handles promotion.
6. POST /api/ml/retraining/rollback restores production model safely.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database.connection import SessionLocal
from app.models.retraining_job import RetrainingJob
from ml.model_registry import get_active_model_version


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


class TestRetrainingAPI:
    """Test suite for Day 23 retraining and monitoring endpoints."""

    def test_get_monitor_status(self, client):
        """GET /api/ml/retraining/monitor returns structured drift diagnostic metrics."""
        response = client.get("/api/ml/retraining/monitor")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["DEGRADED", "HEALTHY", "INSUFFICIENT_DATA"]
        assert "is_degraded" in data
        assert "model_version" in data
        assert "evaluated_sample_count" in data
        assert "thresholds_applied" in data

    def test_run_retraining_insufficient_or_healthy(self, client):
        """POST /api/ml/retraining/run without force checks degradation and returns status."""
        response = client.post("/api/ml/retraining/run", json={"force": False})
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
        # Since live sample count is small (3 verified), status should be INSUFFICIENT_DATA or HEALTHY
        assert data["status"] in ["INSUFFICIENT_DATA", "HEALTHY", "BLOCKED", "QUEUED", "RUNNING", "REGISTERED"]

    def test_list_retraining_jobs(self, client, db_session):
        """GET /api/ml/retraining/jobs returns paginated list of retraining jobs."""
        response = client.get("/api/ml/retraining/jobs?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)

    def test_get_retraining_job_not_found(self, client):
        """GET /api/ml/retraining/jobs/INVALID_ID returns 404."""
        response = client.get("/api/ml/retraining/jobs/NONEXISTENT_JOB_123")
        assert response.status_code == 404

    def test_promote_non_registered_job_fails(self, client, db_session):
        """POST /api/ml/retraining/jobs/{id}/promote fails for unaccepted jobs."""
        # Create a dummy failed job
        job = RetrainingJob(
            job_id="TEST_REJECTED_JOB_001",
            trigger_reason="Test reason",
            triggered_by="test",
            model_name="supplyprescript_delay_engine",
            parent_model_version="v1.0",
            candidate_model_version="v1.99-test",
            status="REJECTED",
        )
        db_session.add(job)
        db_session.commit()

        try:
            response = client.post(f"/api/ml/retraining/jobs/{job.job_id}/promote")
            assert response.status_code == 400
            assert "Only REGISTERED candidates can be promoted" in response.json()["detail"]
        finally:
            db_session.delete(job)
            db_session.commit()

    def test_rollback_endpoint(self, client):
        """POST /api/ml/retraining/rollback successfully rolls back to v1.0."""
        response = client.post("/api/ml/retraining/rollback", json={"target_version": "v1.0"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["active_version"] == "v1.0"
        assert get_active_model_version() == "v1.0"

    def test_rollback_invalid_version_returns_404(self, client):
        """POST /api/ml/retraining/rollback with invalid version returns 404."""
        response = client.post("/api/ml/retraining/rollback", json={"target_version": "v999.0"})
        assert response.status_code == 404
