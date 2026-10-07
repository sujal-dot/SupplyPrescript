from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ModelVersionBase(BaseModel):
    model_name: str = Field(..., max_length=100)
    version: str = Field(..., max_length=50)
    model_type: str = Field(..., max_length=100)
    algorithm: str = Field(..., max_length=100)
    training_date: Optional[datetime] = None
    dataset_version: Optional[str] = Field(None, max_length=50)
    metrics: Optional[Dict[str, Any]] = None
    model_path: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class ModelVersionCreate(ModelVersionBase):
    pass


class ModelVersionResponse(ModelVersionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
