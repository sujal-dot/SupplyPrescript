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

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
