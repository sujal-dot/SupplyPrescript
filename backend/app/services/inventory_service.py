"""Inventory service layer for database querying, filtering, and pagination."""

import math
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.inventory import Inventory


class InventoryService:
    @staticmethod
    def get_inventory(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        product_id: Optional[str] = None,
        inventory_status: Optional[str] = None,
    ) -> Tuple[List[Inventory], int, int]:
        """
        Query inventory records with pagination and optional filtering.
        Returns: (inventory_records, total_count, total_pages)
        """
        query = db.query(Inventory)

        if product_id:
            query = query.filter(Inventory.product_id == product_id.strip())

        if inventory_status:
            query = query.filter(func.lower(Inventory.inventory_status) == inventory_status.lower().strip())

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        offset = (page - 1) * page_size
        inventory_records = query.order_by(Inventory.product_id.asc(), Inventory.inventory_date.asc()).offset(offset).limit(page_size).all()

        return inventory_records, total_count, total_pages
