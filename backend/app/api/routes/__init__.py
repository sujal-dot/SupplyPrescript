from .health import router as health_router
from .suppliers import router as suppliers_router
from .shipments import router as shipments_router
from .inventory import router as inventory_router
from .dashboard import router as dashboard_router

__all__ = [
    "health_router",
    "suppliers_router",
    "shipments_router",
    "inventory_router",
    "dashboard_router",
]
