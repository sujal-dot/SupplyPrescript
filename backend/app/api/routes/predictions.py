"""
SupplyPrescript — Predictions API Router
========================================
Exposes endpoints for running machine learning inference on shipment delay risk.
"""

import logging
from fastapi import APIRouter, status

from app.schemas.prediction import ShipmentPredictionRequest, ShipmentPredictionResult
from app.services.prediction_service import PredictionService

logger = logging.getLogger("app.api.routes.predictions")

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.post(
    "/shipment-delay",
    response_model=ShipmentPredictionResult,
    status_code=status.HTTP_200_OK,
    summary="Predict shipment delay probability and expected delay days",
    description="Runs XGBoost classification and regression models on order-time features to forecast delay probability and delay duration.",
)
def predict_shipment_delay(
    request: ShipmentPredictionRequest,
) -> ShipmentPredictionResult:
    """
    Predict whether a shipment will arrive late and estimate the delay duration in days.
    """
    return PredictionService.predict_shipment_delay(request)
