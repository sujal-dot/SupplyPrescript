"""
Root pytest configuration for SupplyPrescript.
Ensures project root and backend are always on sys.path for test discovery.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

for p in (PROJECT_ROOT, BACKEND_DIR):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

import pytest


def _clean_demo_records():
    try:
        from app.database.connection import SessionLocal
        from app.models.shipment import Shipment
        from app.models.decision import Decision
        from app.models.outcome import Outcome
        from app.models.feedback import Feedback

        db = SessionLocal()
        try:
            demo_shipments = db.query(Shipment).filter(Shipment.shipment_id.like("SHIP-DEMO%")).all()
            for s in demo_shipments:
                decs = db.query(Decision).filter(Decision.shipment_id == s.shipment_id).all()
                for d in decs:
                    db.query(Outcome).filter(
                        (Outcome.decision_id == d.id) | (Outcome.decision_business_id == d.decision_id)
                    ).delete(synchronize_session=False)
                    db.query(Feedback).filter(
                        (Feedback.decision_id == d.decision_id) | (Feedback.shipment_id == s.shipment_id)
                    ).delete(synchronize_session=False)
                    db.delete(d)
                db.delete(s)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_demo_shipments_session():
    _clean_demo_records()
    yield
    _clean_demo_records()

