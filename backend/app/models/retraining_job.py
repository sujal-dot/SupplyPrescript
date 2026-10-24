"""SupplyPrescript — Retraining Job Database Model (Day 23)
======================================================
Persists automatic and on-demand model retraining job executions,
performance degradation diagnostics, candidate validation reports, and promotion outcomes.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database.connection import Base


class RetrainingJob(Base):
    __tablename__ = "retraining_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)
    trigger_reason = Column(String(255), nullable=False)
    triggered_by = Column(String(100), nullable=False, default="system_pipeline")
    model_name = Column(String(100), nullable=False, default="supplyprescript_delay_engine")
    parent_model_version = Column(String(32), nullable=False)
    candidate_model_version = Column(String(32), nullable=True, index=True)
    dataset_version = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, index=True, default="QUEUED")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    baseline_metrics = Column(JSONB, nullable=True)
    candidate_metrics = Column(JSONB, nullable=True)
    acceptance_result = Column(JSONB, nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<RetrainingJob(job_id='{self.job_id}', status='{self.status}', "
            f"parent='{self.parent_model_version}', candidate='{self.candidate_model_version}')>"
        )
