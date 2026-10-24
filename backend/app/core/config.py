from typing import List, Union
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SupplyPrescript"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://supplyprescript:supplyprescript@localhost:5432/supplyprescript"
    POSTGRES_DB: str = "supplyprescript"
    POSTGRES_USER: str = "supplyprescript"
    POSTGRES_PASSWORD: str = "supplyprescript"
    
    # URLs / CORS
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Authentication & Security
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    AUTH_ENABLED: bool = True
    AUTH_REQUIRED: bool = False  # Set to True in production to strictly require Bearer token on all operations
    AUTH_SECRET_KEY: str = "supplyprescript-super-secret-jwt-key-2026-production-hardening"
    AUTH_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ML & Risk Thresholds
    RISK_THRESHOLD_LOW: float = 0.30
    RISK_THRESHOLD_HIGH: float = 0.70
    ACTIVE_MODEL_VERSION: str = "v1.0"

    # Day 23: Continuous Retraining & Drift Monitoring
    RETRAINING_MIN_FEEDBACK_THRESHOLD: int = 10
    RETRAINING_MIN_TRAIN_SAMPLES: int = 50
    RETRAINING_MIN_VAL_SAMPLES: int = 15
    RETRAINING_DEGRADATION_MAE_THRESHOLD_PCT: float = 15.0  # 15% relative MAE degradation
    RETRAINING_DEGRADATION_MAE_ABSOLUTE_DAYS: float = 0.25  # 0.25 days absolute MAE degradation
    RETRAINING_MIN_IMPROVEMENT_PCT: float = 3.0             # Candidate must improve MAE by >= 3%
    RETRAINING_MAX_SECONDARY_REGRESSION_PCT: float = 10.0   # Max allowable regression in secondary metrics
    RETRAINING_COOLDOWN_MINUTES: int = 60                   # Retraining cooldown period
    RETRAINING_MAX_CONCURRENT_JOBS: int = 1
    RETRAINING_AUTO_PROMOTION_ENABLED: bool = False         # Controlled human-reviewed promotion by default
    RETRAINING_CANDIDATES_DIR: str = "ml/artifacts/candidates"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
