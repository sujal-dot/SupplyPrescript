"""Dashboard API router."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse, summary="Get aggregated supply chain metrics and KPIs")
def get_dashboard(db: Session = Depends(get_db)):
    """
    Retrieve aggregated supply-chain KPIs, status breakdowns, and top delayed suppliers from PostgreSQL.
    """
    try:
        metrics = DashboardService.get_dashboard_metrics(db=db)
        return {"data": metrics}
    except Exception as exc:
        logger.error(f"Error computing dashboard metrics: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing dashboard metrics",
        )
