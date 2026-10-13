"""Inventory service layer for database querying, filtering, and pagination."""

import math
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.inventory import Inventory


from app.models.product import Product


class InventoryService:
    @staticmethod
    def get_inventory(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        product_id: Optional[str] = None,
        inventory_status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = "product_id",
        sort_order: Optional[str] = "asc",
    ) -> Tuple[List[Inventory], int, int]:
        """
        Query inventory records with pagination, search, sorting, and optional filtering.
        Returns: (inventory_records, total_count, total_pages)
        """
        query = db.query(Inventory)

        if search:
            term = f"%{search.strip()}%"
            # Match product_id or join with Product
            prod_ids = [p.product_id for p in db.query(Product.product_id).filter(Product.product_name.ilike(term)).all()]
            query = query.filter(Inventory.product_id.ilike(term) | Inventory.product_id.in_(prod_ids))

        if product_id:
            query = query.filter(Inventory.product_id == product_id.strip())

        if inventory_status:
            query = query.filter(func.lower(Inventory.inventory_status) == inventory_status.lower().strip())

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        # Sorting
        sort_col = Inventory.product_id
        if sort_by == "inventory_level":
            sort_col = Inventory.inventory_level
        elif sort_by == "demand":
            sort_col = Inventory.demand
        elif sort_by == "reorder_point":
            sort_col = Inventory.reorder_point

        if sort_order and sort_order.lower() == "desc":
            query = query.order_by(sort_col.desc(), Inventory.id.desc())
        else:
            query = query.order_by(sort_col.asc(), Inventory.id.asc())

        offset = (page - 1) * page_size
        inventory_records = query.offset(offset).limit(page_size).all()

        # Attach product names
        p_ids = [r.product_id for r in inventory_records]
        if p_ids:
            p_map = {p.product_id: p.product_name for p in db.query(Product).filter(Product.product_id.in_(p_ids)).all()}
            for r in inventory_records:
                r.product_name = p_map.get(r.product_id)

        return inventory_records, total_count, total_pages
