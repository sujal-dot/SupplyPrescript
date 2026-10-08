"""Shipment API router."""

import logging
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.shipment import ShipmentListResponse
from app.services.shipment_service import ShipmentService, ALLOWED_SORT_FIELDS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


@router.get("", response_model=ShipmentListResponse, summary="List shipments with pagination, filtering, and sorting")
def get_shipments(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (1 to 100)"),
    supplier_id: Optional[str] = Query(None, description="Filter by supplier ID (e.g. SUP001)"),
    product_id: Optional[str] = Query(None, description="Filter by product ID (e.g. PROD001)"),
    priority: Optional[str] = Query(None, description="Filter by priority (Low, Medium, High, Critical)"),
    transport_mode: Optional[str] = Query(None, description="Filter by transport mode (Road, Rail, Air, Sea)"),
    is_delayed: Optional[bool] = Query(None, description="Filter by delay status (true for delayed, false for on-time)"),
    start_date: Optional[date] = Query(None, description="Filter orders placed on or after start_date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter orders placed on or before end_date (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query("order_date", description="Field to sort by (order_date, quantity, shipping_cost, lead_time, delay_days)"),
    sort_order: Optional[str] = Query("asc", description="Sort direction (asc or desc)"),
    db: Session = Depends(get_db),
):
    """
    Retrieve shipments from PostgreSQL with pagination, multiple filters, date range, and sorting.
    """
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be less than or equal to end_date",
        )

    # Validate sorting fields
    if sort_by and sort_by not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field '{sort_by}'. Allowed fields: {list(ALLOWED_SORT_FIELDS.keys())}",
        )

    if sort_order and sort_order.lower() not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_order must be either 'asc' or 'desc'",
        )

    try:
        shipments, total, total_pages = ShipmentService.get_shipments(
            db=db,
            page=page,
            page_size=page_size,
            supplier_id=supplier_id,
            product_id=product_id,
            priority=priority,
            transport_mode=transport_mode,
            is_delayed=is_delayed,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {
            "data": shipments,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching shipments: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching shipments",
        )
