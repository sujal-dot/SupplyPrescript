"""
SupplyPrescript — Prediction Service Layer
==========================================
Encapsulates machine learning model inference operations, database feature
resolution, scenario validations, and conversion to API domain schemas.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.schemas.prediction import (
    PredictRequest,
    PredictResponse,
    ShipmentPredictionRequest,
    ShipmentPredictionResult,
    determine_risk_category,
)
from ml.feature_config import SEASON_MONTH_MAP, calculate_hub_distance_km
from ml.predict import predict_shipment

logger = logging.getLogger("app.services.prediction_service")


class PredictionService:
    @staticmethod
    def predict_shipment(request: PredictRequest, db: Session) -> PredictResponse:
        """
        Orchestrate production shipment delay prediction (Day 9):
        1. Validate request and resolve supplier and product database records.
        2. Resolve authoritative features (supplier reliability, historical delay, demand, route distance).
        3. Build validated, leak-free feature vector adhering to Day 6 feature schema.
        4. Execute active registered model inference (v1.0 XGBoost classifier & regressor).
        5. Compute calibrated risk category (LOW, MEDIUM, HIGH) via operational thresholds.
        6. Validate prediction outputs and return structured response.
        """
        try:
            # 1. Resolve Supplier
            supplier = (
                db.query(Supplier)
                .filter(
                    (Supplier.id == request.supplier_id)
                    | (Supplier.supplier_id == f"SUP{request.supplier_id:03d}")
                    | (Supplier.supplier_id == str(request.supplier_id))
                )
                .first()
            )
            if not supplier:
                logger.warning("Prediction requested for non-existent supplier_id: %s", request.supplier_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Supplier with ID {request.supplier_id} not found",
                )

            if supplier.supplier_reliability is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Supplier ID {request.supplier_id} is missing a reliability score in the database",
                )
            supplier_reliability = float(supplier.supplier_reliability)

            # 2. Resolve Product
            product = (
                db.query(Product)
                .filter(
                    (Product.id == request.product_id)
                    | (Product.product_id == f"PROD{request.product_id:03d}")
                    | (Product.product_id == str(request.product_id))
                )
                .first()
            )
            if not product:
                logger.warning("Prediction requested for non-existent product_id: %s", request.product_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {request.product_id} not found",
                )

            # 3. Resolve Demand and Inventory Scenario
            if request.demand is not None:
                demand = request.demand
            else:
                # Retrieve latest authoritative inventory record for this product
                latest_inv = (
                    db.query(Inventory)
                    .filter(Inventory.product_id == product.product_id)
                    .order_by(Inventory.inventory_date.desc())
                    .first()
                )
                if latest_inv and latest_inv.demand is not None:
                    demand = int(latest_inv.demand)
                elif product.base_demand is not None:
                    demand = int(round(float(product.base_demand)))
                else:
                    demand = 0

            # 4. Resolve Historical Supplier Performance & Shipment Stats
            stats = (
                db.query(
                    func.count(Shipment.id).label("total_shipments"),
                    func.avg(Shipment.delay_days).label("avg_delay"),
                    func.avg(Shipment.lead_time).label("avg_lead_time"),
                    func.avg(Shipment.shipping_cost).label("avg_shipping_cost"),
                )
                .filter(Shipment.supplier_id == supplier.supplier_id)
                .one()
            )

            # Empirical historical average delay
            if stats.avg_delay is not None:
                historical_avg_delay = round(float(stats.avg_delay), 4)
            else:
                # Neutral training fallback (0.0 days) for suppliers with no prior history
                historical_avg_delay = 0.0

            # Transit Lead Time
            if request.lead_time is not None:
                lead_time = request.lead_time
            elif supplier.base_lead_time is not None and supplier.base_lead_time > 0:
                lead_time = int(supplier.base_lead_time)
            elif stats.avg_lead_time is not None:
                lead_time = max(1, int(round(float(stats.avg_lead_time))))
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Lead time could not be determined for supplier {request.supplier_id}",
                )

            # Destination & Route Distance
            if request.destination:
                dest_city = request.destination.strip().title()
            else:
                # Query most frequent destination for this supplier
                top_dest = (
                    db.query(Shipment.destination)
                    .filter(Shipment.supplier_id == supplier.supplier_id)
                    .group_by(Shipment.destination)
                    .order_by(func.count(Shipment.id).desc())
                    .first()
                )
                dest_city = top_dest[0] if (top_dest and top_dest[0]) else "Delhi"

            orig_city = str(supplier.origin).strip().title()
            distance = float(calculate_hub_distance_km(orig_city, dest_city))

            # Shipping Cost
            if request.shipping_cost is not None:
                shipping_cost = float(request.shipping_cost)
            else:
                prod_ship_cost = (
                    db.query(func.avg(Shipment.shipping_cost))
                    .filter(
                        Shipment.supplier_id == supplier.supplier_id,
                        Shipment.product_id == product.product_id,
                    )
                    .scalar()
                )
                if prod_ship_cost is not None:
                    shipping_cost = round(float(prod_ship_cost), 2)
                elif stats.avg_shipping_cost is not None:
                    shipping_cost = round(float(stats.avg_shipping_cost), 2)
                else:
                    dist_rate = 0.12 if request.transport_mode != "Air" else 0.45
                    weight_kg = float(product.weight_kg) if product.weight_kg else 1.0
                    shipping_cost = round(max(25.0, (distance * dist_rate) + (request.quantity * weight_kg * 0.05)), 2)

            # Priority
            if request.priority:
                priority = request.priority
            else:
                top_prio = (
                    db.query(Shipment.priority)
                    .filter(Shipment.supplier_id == supplier.supplier_id)
                    .group_by(Shipment.priority)
                    .order_by(func.count(Shipment.id).desc())
                    .first()
                )
                priority = top_prio[0] if (top_prio and top_prio[0]) else "Medium"

            # Season
            if request.season:
                season = request.season
            else:
                curr_month = datetime.now(timezone.utc).month
                season = SEASON_MONTH_MAP.get(curr_month, "Winter")

            # 5. Build Validated Feature Vector for Inference
            feature_vector: Dict[str, Any] = {
                "supplier_reliability": supplier_reliability,
                "historical_avg_delay": historical_avg_delay,
                "lead_time": int(lead_time),
                "inventory_level": int(request.inventory_level),
                "demand": int(demand),
                "quantity": int(request.quantity),
                "shipping_cost": float(shipping_cost),
                "distance": float(distance),
                "transport_mode": request.transport_mode,
                "season": season,
                "priority": priority,
            }

            # 6. Execute ML Inference
            pred_raw = predict_shipment(feature_vector)
            prob = float(pred_raw["delay_probability"])
            days = float(pred_raw["predicted_delay_days"])
            model_v = str(pred_raw.get("model_version", settings.ACTIVE_MODEL_VERSION))

            # 7. Output Validations
            if not (0.0 <= prob <= 1.0) or math.isnan(prob) or math.isinf(prob):
                raise ValueError(f"Classifier generated invalid delay probability: {prob}")
            if days < 0.0 or math.isnan(days) or math.isinf(days):
                raise ValueError(f"Regressor generated invalid delay days: {days}")

            # 8. Categorize Risk
            risk = determine_risk_category(
                prob,
                low_threshold=settings.RISK_THRESHOLD_LOW,
                high_threshold=settings.RISK_THRESHOLD_HIGH,
            )

            # 9. Return Response
            return PredictResponse(
                delay_probability=round(prob, 4),
                predicted_delay_days=round(days, 2),
                risk=risk,
                model_version=model_v,
                prediction_id=f"PRED-{uuid.uuid4().hex[:12].upper()}",
                prediction_timestamp=datetime.now(timezone.utc).isoformat(),
                features_used=feature_vector,
            )

        except HTTPException:
            raise
        except FileNotFoundError as fnf_err:
            logger.error("Prediction failed: model artifacts not found: %s", fnf_err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Predictive ML model artifacts are unavailable: {str(fnf_err)}",
            )
        except ValueError as val_err:
            logger.warning("Prediction input/feature validation error: %s", val_err)
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

    @staticmethod
    def predict_shipment_delay(request: ShipmentPredictionRequest) -> ShipmentPredictionResult:
        """
        Legacy Day 7 endpoint logic: runs delay classification and regression on raw feature vector.
        """
        try:
            payload = request.model_dump()
            res_dict = predict_shipment(payload)
            return ShipmentPredictionResult(**res_dict)

        except HTTPException:
            raise
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
