"""Shipment service layer for database querying, filtering, sorting, and pagination."""

import math
from datetime import date
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.shipment import Shipment

ALLOWED_SORT_FIELDS = {
    "order_date": Shipment.order_date,
    "quantity": Shipment.quantity,
    "shipping_cost": Shipment.shipping_cost,
    "lead_time": Shipment.lead_time,
    "delay_days": Shipment.delay_days,
}


class ShipmentService:
    @staticmethod
    def get_shipments(
        db: Session,
        page: int = 1,
        page_size: int = 50,
        supplier_id: Optional[str] = None,
        product_id: Optional[str] = None,
        priority: Optional[str] = None,
        transport_mode: Optional[str] = None,
        is_delayed: Optional[bool] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_by: Optional[str] = "order_date",
        sort_order: Optional[str] = "asc",
    ) -> Tuple[List[Shipment], int, int]:
        """
        Query shipments with pagination, filtering, date range, and sorting.
        Returns: (shipments, total_count, total_pages)
        """
        query = db.query(Shipment)

        if supplier_id:
            query = query.filter(Shipment.supplier_id == supplier_id.strip())

        if product_id:
            query = query.filter(Shipment.product_id == product_id.strip())

        if priority:
            query = query.filter(func.lower(Shipment.priority) == priority.lower().strip())

        if transport_mode:
            query = query.filter(func.lower(Shipment.transport_mode) == transport_mode.lower().strip())

        if is_delayed is not None:
            if is_delayed:
                query = query.filter(Shipment.delay_days > 0)
            else:
                query = query.filter(Shipment.delay_days == 0)

        if start_date is not None:
            query = query.filter(Shipment.order_date >= start_date)

        if end_date is not None:
            query = query.filter(Shipment.order_date <= end_date)

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        # Sorting using allowlist
        sort_column = ALLOWED_SORT_FIELDS.get(sort_by, Shipment.order_date)
        if sort_order and sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc(), Shipment.id.desc())
        else:
            query = query.order_by(sort_column.asc(), Shipment.id.asc())

        offset = (page - 1) * page_size
        shipments = query.offset(offset).limit(page_size).all()

        return shipments, total_count, total_pages
