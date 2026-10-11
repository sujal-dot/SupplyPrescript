"""
SupplyPrescript — Feature Engineering Configuration
===================================================
Centralized configuration for Day 6 feature engineering pipeline.
Defines input/output paths, feature column specifications, seasonal calendars,
route distance calculation parameters, chronological split thresholds, and leakage guards.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Path Configuration
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ML_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

PROCESSED_DATA_DIR = DATA_DIR / "processed"
DEFAULT_INPUT_PATH = PROCESSED_DATA_DIR / "shipments_processed.csv"

FEATURES_DIR = DATA_DIR / "features"
REGRESSION_DIR = FEATURES_DIR / "regression"
CLASSIFICATION_DIR = FEATURES_DIR / "classification"
METADATA_DIR = FEATURES_DIR / "metadata"

PREPROCESSOR_ARTIFACT_PATH = METADATA_DIR / "preprocessor.joblib"
FEATURE_SCHEMA_PATH = METADATA_DIR / "feature_schema.json"
FEATURE_REPORT_PATH = METADATA_DIR / "feature_report.json"
SPLIT_METADATA_PATH = METADATA_DIR / "split_metadata.json"
LEAKAGE_REPORT_PATH = METADATA_DIR / "leakage_report.json"

ARTIFACTS_DIR = ML_DIR / "artifacts"
CLASSIFICATION_ARTIFACTS_DIR = ARTIFACTS_DIR / "classification"
REGRESSION_ARTIFACTS_DIR = ARTIFACTS_DIR / "regression"

REPORTS_DIR = ML_DIR / "reports"
CLASSIFICATION_REPORTS_DIR = REPORTS_DIR / "classification"
REGRESSION_REPORTS_DIR = REPORTS_DIR / "regression"

MODELS_ROOT_DIR = PROJECT_ROOT / "models"
MODEL_VERSIONS_DIR = MODELS_ROOT_DIR / "versions"
PRIMARY_COMPATIBILITY_MODEL_PATH = MODELS_ROOT_DIR / "xgboost_delay_model.pkl"
ACTIVE_VERSION_POINTER_PATH = MODEL_VERSIONS_DIR / "active.json"

# ---------------------------------------------------------------------------
# Feature Lists & Schema Definitions
# ---------------------------------------------------------------------------
# The 11 approved features for Day 6
NUMERICAL_FEATURES: List[str] = [
    "supplier_reliability",
    "historical_avg_delay",
    "lead_time",
    "inventory_level",
    "demand",
    "quantity",
    "shipping_cost",
    "distance",
]

CATEGORICAL_FEATURES: List[str] = [
    "transport_mode",
    "season",
    "priority",
]

APPROVED_FEATURES: List[str] = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

# Targets
REGRESSION_TARGET: str = "delay_days"
CLASSIFICATION_TARGET: str = "delayed"

# Column ordering for saved datasets
REGRESSION_COLUMNS: List[str] = APPROVED_FEATURES + [REGRESSION_TARGET]
CLASSIFICATION_COLUMNS: List[str] = APPROVED_FEATURES + [CLASSIFICATION_TARGET]

# ---------------------------------------------------------------------------
# Chronological Split Configuration
# ---------------------------------------------------------------------------
TRAIN_RATIO: float = 0.70
VAL_RATIO: float = 0.15
TEST_RATIO: float = 0.15
RANDOM_SEED: int = 42

# Critical date & ID columns used for sorting and validation
ORDER_DATE_COL: str = "order_date"
EXPECTED_DELIVERY_DATE_COL: str = "expected_delivery_date"
ACTUAL_DELIVERY_DATE_COL: str = "actual_delivery_date"
SUPPLIER_ID_COL: str = "supplier_id"
SHIPMENT_ID_COL: str = "shipment_id"
PRODUCT_ID_COL: str = "product_id"

# ---------------------------------------------------------------------------
# Seasonal Calendar Definitions (Indian Logistics Climate)
# ---------------------------------------------------------------------------
SEASON_MONTH_MAP: Dict[int, str] = {
    12: "Winter",
    1: "Winter",
    2: "Winter",
    3: "Summer",
    4: "Summer",
    5: "Summer",
    6: "Monsoon",
    7: "Monsoon",
    8: "Monsoon",
    9: "Monsoon",
    10: "Post-Monsoon",
    11: "Post-Monsoon",
}

VALID_SEASONS: Set[str] = {"Winter", "Summer", "Monsoon", "Post-Monsoon"}
VALID_TRANSPORT_MODES: Set[str] = {"Road", "Rail", "Air", "Sea"}
VALID_PRIORITIES: Set[str] = {"Low", "Medium", "High", "Critical"}

# ---------------------------------------------------------------------------
# Route Distance & Logistics Hubs Coordinates
# ---------------------------------------------------------------------------
# Validated Indian logistics hubs coordinates
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Delhi": (28.7041, 77.1025),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714),
    "Surat": (21.1702, 72.8311),
    "Nagpur": (21.1458, 79.0882),
    "Kolkata": (22.5726, 88.3639),
    "Jaipur": (26.9124, 75.7873),
    "Indore": (22.7196, 75.8577),
    "Nashik": (19.9975, 73.7898),
    "Vadodara": (22.3072, 73.1812),
    "Noida": (28.5355, 77.3910),
    "Gurugram": (28.4595, 77.0266),
}

EARTH_RADIUS_KM: float = 6371.0
HIGHWAY_CIRCUITY_FACTOR: float = 1.25
INTRA_CITY_MIN_DISTANCE_KM: int = 35


def calculate_hub_distance_km(orig: str, dest: str) -> float:
    """
    Calculate realistic transit route distance (in km) between logistics hubs using
    the Haversine great-circle formula with a standard highway circuity factor (1.25).
    """
    if not orig or not dest:
        return float(INTRA_CITY_MIN_DISTANCE_KM)

    orig_clean = str(orig).strip()
    dest_clean = str(dest).strip()

    if orig_clean == dest_clean:
        return float(INTRA_CITY_MIN_DISTANCE_KM)

    if orig_clean not in CITY_COORDINATES or dest_clean not in CITY_COORDINATES:
        # Unknown city fallback estimate
        return float(INTRA_CITY_MIN_DISTANCE_KM)

    lat1, lon1 = CITY_COORDINATES[orig_clean]
    lat2, lon2 = CITY_COORDINATES[dest_clean]

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = EARTH_RADIUS_KM * c * HIGHWAY_CIRCUITY_FACTOR
    return max(float(INTRA_CITY_MIN_DISTANCE_KM), round(distance, 2))


# ---------------------------------------------------------------------------
# Data Leakage Blacklist
# ---------------------------------------------------------------------------
# Fields that must NEVER enter the feature matrix X for order-time prediction
LEAKAGE_COLUMNS: Set[str] = {
    "actual_delivery_date",
    "delivery_status",
    "is_delayed",
    "delay_days",
    "delayed",
    "delay_reason",
    "lead_time_outlier",
}

# Identifier columns to keep separate from predictive numerical feature inputs
IDENTIFIER_COLUMNS: Set[str] = {
    "shipment_id",
    "supplier_id",
    "product_id",
}
