"""Inventory API router."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.inventory import InventoryListResponse
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.get("", response_model=InventoryListResponse, summary="List inventory records with pagination and filtering")
def get_inventory(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1 to 100)"),
    product_id: Optional[str] = Query(None, description="Filter by product ID (e.g. PROD001)"),
    inventory_status: Optional[str] = Query(None, description="Filter by status (Healthy, Low, Critical, Out of Stock)"),
    search: Optional[str] = Query(None, description="Search product ID or product name"),
    sort_by: Optional[str] = Query("product_id", description="Sort by product_id, inventory_level, demand, or reorder_point"),
    sort_order: Optional[str] = Query("asc", description="Sort direction asc or desc"),
    db: Session = Depends(get_db),
):
    """
    Retrieve inventory records from PostgreSQL with pagination and optional filtering by product ID and status.
    """
    try:
        inventory_records, total, total_pages = InventoryService.get_inventory(
            db=db,
            page=page,
            page_size=page_size,
            product_id=product_id,
            inventory_status=inventory_status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {
            "data": inventory_records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as exc:
        logger.error(f"Error fetching inventory: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching inventory records",
        )
