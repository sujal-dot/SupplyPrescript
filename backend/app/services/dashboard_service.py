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

        # Delay trends by month
        trend_rows = db.query(
            func.to_char(Shipment.order_date, 'YYYY-MM').label("month"),
            func.avg(Shipment.delay_days).label("avg_delay"),
            func.sum(case((Shipment.delay_days > 0, 1), else_=0)).label("delayed_count"),
            func.count(Shipment.id).label("total")
        ).group_by("month").order_by("month").all()

        delay_trends = [
            {
                "month": r.month,
                "average_delay_days": round(float(r.avg_delay or 0.0), 2),
                "delayed_shipments": int(r.delayed_count or 0),
                "total_shipments": int(r.total or 0),
            }
            for r in trend_rows
        ]

        # Top 8 reliable suppliers with shipment counts
        rel_rows = db.query(
            Supplier.supplier_id,
            Supplier.supplier_name,
            Supplier.supplier_reliability,
            func.count(Shipment.id).label("shipment_count")
        ).outerjoin(
            Shipment, Supplier.supplier_id == Shipment.supplier_id
        ).group_by(
            Supplier.id, Supplier.supplier_id, Supplier.supplier_name, Supplier.supplier_reliability
        ).order_by(
            desc(Supplier.supplier_reliability)
        ).limit(8).all()

        supplier_reliability_rankings = [
            {
                "supplier_id": r.supplier_id,
                "supplier_name": r.supplier_name,
                "reliability": round(float(r.supplier_reliability), 4) if r.supplier_reliability is not None else 0.0,
                "shipment_count": int(r.shipment_count or 0),
            }
            for r in rel_rows
        ]

        # Overall average supplier reliability
        avg_supp_rel = db.query(func.avg(Supplier.supplier_reliability)).scalar()
        average_supplier_reliability = round(float(avg_supp_rel), 4) if avg_supp_rel is not None else 0.0

        # Predictions risk distribution and high-risk shipments
        from app.models.prediction import Prediction
        pred_rows = db.query(Prediction).all()
        low_count = 0
        med_count = 0
        high_count = 0
        high_risk_shipments = []
        for p in pred_rows:
            prob = float(p.prediction_probability) if p.prediction_probability is not None else 0.0
            if prob < 0.30:
                low_count += 1
                risk_lvl = "LOW"
            elif prob < 0.70:
                med_count += 1
                risk_lvl = "MEDIUM"
            else:
                high_count += 1
                risk_lvl = "HIGH"
                ship = db.query(Shipment).filter(Shipment.shipment_id == p.shipment_id).first()
                high_risk_shipments.append({
                    "shipment_id": p.shipment_id,
                    "supplier_id": ship.supplier_id if ship else "N/A",
                    "product_id": ship.product_id if ship else "N/A",
                    "delay_probability": round(prob, 4),
                    "predicted_delay_days": round(float(p.predicted_value), 2),
                    "risk_level": risk_lvl,
                })

        risk_distribution = {
            "LOW": low_count,
            "MEDIUM": med_count,
            "HIGH": high_count,
        }

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
            "delay_trends": delay_trends,
            "supplier_reliability_rankings": supplier_reliability_rankings,
            "average_supplier_reliability": average_supplier_reliability,
            "risk_distribution": risk_distribution,
            "high_risk_shipments": high_risk_shipments,
        }
