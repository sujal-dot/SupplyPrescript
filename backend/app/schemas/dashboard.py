from typing import Dict, List
from pydantic import BaseModel, ConfigDict


class TopDelayedSupplier(BaseModel):
    supplier_id: str
    shipment_count: int
    delayed_shipments: int
    delay_rate: float

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

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    data: DashboardMetrics

    model_config = ConfigDict(from_attributes=True)
