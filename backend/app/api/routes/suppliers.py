"""Supplier API router."""

import logging
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.supplier import SupplierListResponse
from app.services.supplier_service import SupplierService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])


@router.get("", response_model=SupplierListResponse, summary="List suppliers with pagination and filtering")
def get_suppliers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1 to 100)"),
    origin: Optional[str] = Query(None, description="Filter by origin city"),
    min_reliability: Optional[Decimal] = Query(None, ge=0, le=1, description="Filter by minimum supplier reliability (0.0 to 1.0)"),
    db: Session = Depends(get_db),
):
    """
    Retrieve suppliers from PostgreSQL with pagination and optional filtering by origin and reliability.
    """
    try:
        suppliers, total, total_pages = SupplierService.get_suppliers(
            db=db,
            page=page,
            page_size=page_size,
            origin=origin,
            min_reliability=min_reliability,
        )
        return {
            "data": suppliers,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as exc:
        logger.error(f"Error fetching suppliers: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching suppliers",
        )
