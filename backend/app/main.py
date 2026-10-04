from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.health import router as health_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Supply Chain Analytics & Prescription Platform API",
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


# Include health routes (/health, /health/db)
app.include_router(health_router)
