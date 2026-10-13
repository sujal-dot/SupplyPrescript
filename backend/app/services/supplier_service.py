"""Supplier service layer for database querying and pagination."""

import math
from typing import Optional, Tuple, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.supplier import Supplier


from app.models.shipment import Shipment
from sqlalchemy import case, desc


class SupplierService:
    @staticmethod
    def get_suppliers(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        origin: Optional[str] = None,
        min_reliability: Optional[Decimal] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = "supplier_id",
        sort_order: Optional[str] = "asc",
    ) -> Tuple[List[Supplier], int, int]:
        """
        Query suppliers with pagination, optional filtering, search, and sorting.
        Returns: (suppliers, total_count, total_pages)
        """
        query = db.query(Supplier)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Supplier.supplier_name.ilike(term) | Supplier.supplier_id.ilike(term)
            )

        if origin:
            query = query.filter(func.lower(Supplier.origin) == origin.lower().strip())

        if min_reliability is not None:
            query = query.filter(Supplier.supplier_reliability >= min_reliability)

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        # Sort field handling
        sort_col = Supplier.supplier_id
        if sort_by == "reliability":
            sort_col = Supplier.supplier_reliability
        elif sort_by == "supplier_name":
            sort_col = Supplier.supplier_name

        if sort_order and sort_order.lower() == "desc":
            query = query.order_by(sort_col.desc(), Supplier.id.desc())
        else:
            query = query.order_by(sort_col.asc(), Supplier.id.asc())

        offset = (page - 1) * page_size
        suppliers = query.offset(offset).limit(page_size).all()

        # Compute aggregate shipment metrics for returned suppliers
        sup_ids = [s.supplier_id for s in suppliers]
        if sup_ids:
            stats = (
                db.query(
                    Shipment.supplier_id,
                    func.count(Shipment.id).label("total_shipments"),
                    func.avg(Shipment.delay_days).label("avg_delay"),
                    func.sum(case((Shipment.delay_days > 0, 1), else_=0)).label("delayed_count"),
                )
                .filter(Shipment.supplier_id.in_(sup_ids))
                .group_by(Shipment.supplier_id)
                .all()
            )
            stats_map = {
                r.supplier_id: {
                    "total_shipments": int(r.total_shipments or 0),
                    "avg_delay": round(float(r.avg_delay or 0.0), 2),
                    "delayed_count": int(r.delayed_count or 0),
                }
                for r in stats
            }
            for s in suppliers:
                st = stats_map.get(s.supplier_id, {})
                s.total_shipments = st.get("total_shipments", 0)
                s.historical_avg_delay = st.get("avg_delay", 0.0)
                s.delayed_shipment_count = st.get("delayed_count", 0)

        return suppliers, total_count, total_pages
