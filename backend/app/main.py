from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.suppliers import router as suppliers_router
from app.api.routes.shipments import router as shipments_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.dashboard import router as dashboard_router

app = FastAPI(
    title="SupplyPrescript API",
    description="Supply chain analytics and prescription API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + [settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint verifying API availability."""
    return {"message": "SupplyPrescript API is running"}


# Include routes
app.include_router(health_router)
app.include_router(suppliers_router)
app.include_router(shipments_router)
app.include_router(inventory_router)
app.include_router(dashboard_router)
