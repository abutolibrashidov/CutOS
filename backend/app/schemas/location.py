"""Location Pydantic schemas for admin location management."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    is_active: bool = True


class LocationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    address: str | None = None
    city: str | None = None
    is_active: bool
    created_at: datetime
