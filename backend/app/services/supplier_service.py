"""Supplier service layer for database querying and pagination."""

import math
from typing import Optional, Tuple, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.supplier import Supplier


class SupplierService:
    @staticmethod
    def get_suppliers(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        origin: Optional[str] = None,
        min_reliability: Optional[Decimal] = None,
    ) -> Tuple[List[Supplier], int, int]:
        """
        Query suppliers with pagination and optional filtering.
        Returns: (suppliers, total_count, total_pages)
        """
        query = db.query(Supplier)

        if origin:
            query = query.filter(func.lower(Supplier.origin) == origin.lower().strip())

        if min_reliability is not None:
            query = query.filter(Supplier.supplier_reliability >= min_reliability)

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        offset = (page - 1) * page_size
        suppliers = query.order_by(Supplier.supplier_id.asc()).offset(offset).limit(page_size).all()

        return suppliers, total_count, total_pages
