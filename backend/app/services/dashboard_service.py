"""Dashboard service layer for aggregated supply chain metrics from PostgreSQL."""

from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc, text
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.inventory import Inventory


class DashboardService:
    @staticmethod
    def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
        """
        Compute high-level aggregated supply-chain KPIs using SQL aggregation.
        Never loads entire datasets into Python memory.
        """
        # Entity counts
        total_shipments = db.query(func.count(Shipment.id)).scalar() or 0
        total_suppliers = db.query(func.count(Supplier.id)).scalar() or 0
        total_products = db.query(func.count(Product.id)).scalar() or 0
        total_inventory_records = db.query(func.count(Inventory.id)).scalar() or 0

        # Shipment aggregations
        shipment_stats = db.query(
            func.sum(case((Shipment.delay_days > 0, 1), else_=0)).label("delayed_shipments"),
            func.sum(case((Shipment.delay_days == 0, 1), else_=0)).label("on_time_shipments"),
            func.avg(Shipment.delay_days).label("avg_delay_days"),
            func.avg(Shipment.lead_time).label("avg_lead_time"),
            func.sum(Shipment.shipping_cost).label("total_shipping_cost"),
            func.avg(Shipment.shipping_cost).label("avg_shipping_cost"),
            func.sum(case((Shipment.inventory_level < Shipment.demand, 1), else_=0)).label("inventory_shortage_count"),
        ).first()

        delayed_shipments = int(shipment_stats.delayed_shipments or 0) if shipment_stats else 0
        on_time_shipments = int(shipment_stats.on_time_shipments or 0) if shipment_stats else 0
        delay_rate = round(float(delayed_shipments / total_shipments), 4) if total_shipments > 0 else 0.0
        avg_delay_days = round(float(shipment_stats.avg_delay_days or 0.0), 2) if shipment_stats else 0.0
        avg_lead_time = round(float(shipment_stats.avg_lead_time or 0.0), 2) if shipment_stats else 0.0
        total_shipping_cost = round(float(shipment_stats.total_shipping_cost or 0.0), 2) if shipment_stats else 0.0
        avg_shipping_cost = round(float(shipment_stats.avg_shipping_cost or 0.0), 2) if shipment_stats else 0.0
        inventory_shortage_count = int(shipment_stats.inventory_shortage_count or 0) if shipment_stats else 0
        inventory_shortage_rate = round(float(inventory_shortage_count / total_shipments), 4) if total_shipments > 0 else 0.0

        # Breakdowns: transport mode
        tm_rows = db.query(
            Shipment.transport_mode,
            func.count(Shipment.id)
        ).group_by(Shipment.transport_mode).all()
        shipments_by_transport_mode = {mode: count for mode, count in tm_rows}

        # Breakdowns: priority
        prio_rows = db.query(
            Shipment.priority,
            func.count(Shipment.id)
        ).group_by(Shipment.priority).all()
        shipments_by_priority = {prio: count for prio, count in prio_rows}

        # Breakdowns: delivery status
        shipments_by_delivery_status = {
            "on_time": on_time_shipments,
            "delayed": delayed_shipments,
        }

        # Top 5 delayed suppliers
        top_delayed_rows = db.query(
            Shipment.supplier_id,
            func.count(Shipment.id).label("shipment_count"),
            func.sum(case((Shipment.delay_days > 0, 1), else_=0)).label("delayed_shipments"),
            (func.sum(case((Shipment.delay_days > 0, 1.0), else_=0.0)) / func.count(Shipment.id)).label("delay_rate")
        ).group_by(Shipment.supplier_id).order_by(desc("delayed_shipments")).limit(5).all()

        top_delayed_suppliers = [
            {
                "supplier_id": row.supplier_id,
                "shipment_count": int(row.shipment_count),
                "delayed_shipments": int(row.delayed_shipments),
                "delay_rate": round(float(row.delay_rate), 4),
            }
            for row in top_delayed_rows
        ]

        return {
            "total_shipments": total_shipments,
            "total_suppliers": total_suppliers,
            "total_products": total_products,
            "total_inventory_records": total_inventory_records,
            "delayed_shipments": delayed_shipments,
            "on_time_shipments": on_time_shipments,
            "delay_rate": delay_rate,
            "average_delay_days": avg_delay_days,
            "average_lead_time": avg_lead_time,
            "total_shipping_cost": total_shipping_cost,
            "average_shipping_cost": avg_shipping_cost,
            "inventory_shortage_count": inventory_shortage_count,
            "inventory_shortage_rate": inventory_shortage_rate,
            "shipments_by_transport_mode": shipments_by_transport_mode,
            "shipments_by_priority": shipments_by_priority,
            "shipments_by_delivery_status": shipments_by_delivery_status,
            "top_delayed_suppliers": top_delayed_suppliers,
        }
