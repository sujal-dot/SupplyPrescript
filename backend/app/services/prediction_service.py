"""
SupplyPrescript — Prediction Service Layer
==========================================
Encapsulates machine learning model inference operations, lifecycle loading,
and conversion to API domain schemas.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.prediction import ShipmentPredictionRequest, ShipmentPredictionResult
from ml.predict import predict_shipment

logger = logging.getLogger("app.services.prediction_service")


class PredictionService:
    @staticmethod
    def predict_shipment_delay(request: ShipmentPredictionRequest) -> ShipmentPredictionResult:
        """
        Run delay classification and delay days regression on shipment features.
        """
        try:
            payload = request.model_dump()
            res_dict = predict_shipment(payload)
            return ShipmentPredictionResult(**res_dict)

        except FileNotFoundError as fnf_err:
            logger.error("Prediction failed because model artifacts were not found: %s", fnf_err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Predictive ML model artifacts are unavailable: {str(fnf_err)}",
            )
        except ValueError as val_err:
            logger.warning("Prediction input validation error: %s", val_err)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(val_err),
            )
        except Exception as exc:
            logger.error("Unexpected error during shipment prediction: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred while generating shipment delay prediction",
            )
