"""Admin Pydantic schemas for Barber management."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AdminBarberCreate(BaseModel):
    telegram_id: int = Field(..., gt=0, description="Telegram numeric user ID")
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=30)
    location_id: uuid.UUID | None = None
    bio: str | None = None
    avatar_url: str | None = None
    is_active: bool = True


class AdminBarberUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=30)
    location_id: uuid.UUID | None = None
    bio: str | None = None
    avatar_url: str | None = None
    is_active: bool | None = None


class AdminBarberStatusUpdate(BaseModel):
    is_active: bool


class AdminBarberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    location_id: uuid.UUID | None
    telegram_id: int
    full_name: str
    phone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime
    location_name: str | None = None
