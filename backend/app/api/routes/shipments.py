"""Shipment API router."""

import logging
import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.schemas.shipment import ShipmentCreate, ShipmentListResponse, ShipmentResponse
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
    search: Optional[str] = Query(None, description="Search by shipment ID"),
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
            search=search,
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


@router.post(
    "",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shipment record (Day 25 Integration)",
    description="Validates supplier, product, dates, and costs before persisting to PostgreSQL operational database.",
)
def create_shipment(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    # 1. Resolve foreign keys
    supplier = db.query(Supplier).filter(Supplier.supplier_id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{payload.supplier_id}' does not exist.",
        )
    product = db.query(Product).filter(Product.product_id == payload.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{payload.product_id}' does not exist.",
        )

    # 2. Check for unique shipment_id
    shipment_id = payload.shipment_id.strip() if payload.shipment_id else f"SHIP-{uuid.uuid4().hex[:8].upper()}"
    existing = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shipment with ID '{shipment_id}' already exists.",
        )

    # 3. Create model
    actual_date = payload.actual_delivery_date or payload.expected_delivery_date
    new_shipment = Shipment(
        shipment_id=shipment_id,
        supplier_id=payload.supplier_id,
        product_id=payload.product_id,
        origin=payload.origin,
        destination=payload.destination,
        order_date=payload.order_date,
        expected_delivery_date=payload.expected_delivery_date,
        actual_delivery_date=actual_date,
        lead_time=payload.lead_time,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        shipping_cost=payload.shipping_cost,
        supplier_reliability=payload.supplier_reliability,
        inventory_level=payload.inventory_level,
        demand=payload.demand,
        priority=payload.priority,
        transport_mode=payload.transport_mode,
        delay_days=payload.delay_days,
    )
    db.add(new_shipment)
    db.commit()
    db.refresh(new_shipment)
    return ShipmentResponse.model_validate(new_shipment)


@router.get(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    summary="Get shipment details by ID",
    description="Retrieve a single shipment from PostgreSQL by unique shipment identifier.",
)
def get_shipment_by_id(
    shipment_id: str,
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id.strip()).first()
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment '{shipment_id}' not found.",
        )
    return ShipmentResponse.model_validate(shipment)
