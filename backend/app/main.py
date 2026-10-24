"""
SupplyPrescript — Main FastAPI Application
==========================================
Core entrypoint configuring CORS, request correlation IDs (X-Request-ID),
standardized error handling, security headers, and router registrations.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.decisions import router as decisions_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.health import router as health_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.optimization import router as optimization_router
from app.api.routes.outcomes import router as outcomes_router
from app.api.routes.predictions import router as predictions_router
from app.api.routes.products import router as products_router
from app.api.routes.retraining import router as retraining_router
from app.api.routes.shipments import router as shipments_router
from app.api.routes.suppliers import router as suppliers_router

logger = logging.getLogger("app.main")

app = FastAPI(
    title="SupplyPrescript API",
    description="Supply chain analytics, prescription, and closed-loop optimization platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request carries a unique X-Request-ID correlation identifier.
    Attaches the ID to request.state and the outgoing HTTP response header.
    """

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = f"req-{uuid.uuid4().hex[:16]}"
        request.state.request_id = req_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


app.add_middleware(CorrelationIdMiddleware)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + [settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


def _status_to_error_code(status_code: int) -> str:
    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        503: "SERVICE_UNAVAILABLE",
        500: "INTERNAL_SERVER_ERROR",
    }
    return codes.get(status_code, f"ERROR_{status_code}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:16]}")
    code = _status_to_error_code(exc.status_code)
    msg = str(exc.detail) if isinstance(exc.detail, str) else "Request failed"

    logger.warning("HTTP %d [%s] on %s %s: %s", exc.status_code, req_id, request.method, request.url.path, msg)

    content: Dict[str, Any] = {
        "detail": exc.detail,
        "error": {
            "code": code,
            "message": msg,
            "request_id": req_id,
        },
    }
    headers = {"X-Request-ID": req_id}
    if exc.headers:
        headers.update(exc.headers)

    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:16]}")
    serializable_errors = jsonable_encoder(exc.errors())
    logger.warning("Validation error [%s] on %s %s: %s", req_id, request.method, request.url.path, serializable_errors)

    content = {
        "detail": serializable_errors,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Input validation failed. Please check the supplied parameters.",
            "details": serializable_errors,
            "request_id": req_id,
        },
    }
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=content,
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:16]}")
    # Secure logging: Log internal details on server, never return trace to client
    logger.error("Unhandled internal exception [%s] on %s %s: %s", req_id, request.method, request.url.path, exc, exc_info=True)

    content = {
        "detail": "An internal server error occurred. Please contact support referencing the request ID.",
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred.",
            "request_id": req_id,
        },
    }
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
        headers={"X-Request-ID": req_id},
    )


@app.get("/")
def root():
    """Root endpoint verifying API availability."""
    return {"message": "SupplyPrescript API is running"}


# Include routes
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(suppliers_router)
app.include_router(shipments_router)
app.include_router(inventory_router)
app.include_router(dashboard_router)
app.include_router(predictions_router)
app.include_router(products_router)
app.include_router(optimization_router)
app.include_router(decisions_router)
app.include_router(outcomes_router)
app.include_router(analytics_router)
app.include_router(feedback_router)
app.include_router(retraining_router)
