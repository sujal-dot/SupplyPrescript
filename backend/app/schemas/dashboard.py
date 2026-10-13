from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class TopDelayedSupplier(BaseModel):
    supplier_id: str
    shipment_count: int
    delayed_shipments: int
    delay_rate: float

    model_config = ConfigDict(from_attributes=True)


class DelayTrendPoint(BaseModel):
    month: str
    average_delay_days: float
    delayed_shipments: int
    total_shipments: int

    model_config = ConfigDict(from_attributes=True)


class SupplierReliabilityRanking(BaseModel):
    supplier_id: str
    supplier_name: str
    reliability: float
    shipment_count: int

    model_config = ConfigDict(from_attributes=True)


class HighRiskShipmentSummary(BaseModel):
    shipment_id: str
    supplier_id: str
    product_id: str
    delay_probability: float
    predicted_delay_days: float
    risk_level: str

    model_config = ConfigDict(from_attributes=True)


class DashboardMetrics(BaseModel):
    total_shipments: int
    total_suppliers: int
    total_products: int
    total_inventory_records: int
    delayed_shipments: int
    on_time_shipments: int
    delay_rate: float
    average_delay_days: float
    average_lead_time: float
    total_shipping_cost: float
    average_shipping_cost: float
    inventory_shortage_count: int
    inventory_shortage_rate: float
    shipments_by_transport_mode: Dict[str, int]
    shipments_by_priority: Dict[str, int]
    shipments_by_delivery_status: Dict[str, int]
    top_delayed_suppliers: List[TopDelayedSupplier]
    delay_trends: Optional[List[DelayTrendPoint]] = None
    supplier_reliability_rankings: Optional[List[SupplierReliabilityRanking]] = None
    average_supplier_reliability: Optional[float] = None
    risk_distribution: Optional[Dict[str, int]] = None
    high_risk_shipments: Optional[List[HighRiskShipmentSummary]] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    data: DashboardMetrics

    model_config = ConfigDict(from_attributes=True)
