from fastapi import APIRouter, HTTPException, status
from app.database.connection import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health():
    """Health check endpoint for the API service."""
    return {"status": "healthy"}


@router.get("/health/db")
def get_db_health():
    """Health check endpoint that tests connectivity to PostgreSQL database."""
    try:
        is_connected = check_db_connection()
        if not is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "unhealthy", "database": "disconnected"}
            )
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(exc)
            }
        )
