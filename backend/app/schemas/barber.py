from datetime import datetime, time, timezone
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Profile Schemas ─────────────────────────────────────────────────────────
class BarberProfileResponse(BaseModel):
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

class BarberProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=30)
    bio: str | None = None
    avatar_url: str | None = None


# ── Service Schemas ─────────────────────────────────────────────────────────
class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    barber_id: uuid.UUID
    name: str
    price_uzs: int
    duration_minutes: int
    is_active: bool
    created_at: datetime

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price_uzs: int = Field(..., ge=0, description="Price in UZS (must be non-negative)")
    duration_minutes: int = Field(..., gt=0, description="Duration in minutes (must be positive)")


class ServiceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    price_uzs: int | None = Field(None, ge=0)
    duration_minutes: int | None = Field(None, gt=0)
    is_active: bool | None = None


# ── Working Schedule Schemas ──────────────────────────────────────────────────
class WorkingScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    barber_id: uuid.UUID
    weekday: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time | None = None
    end_time: time | None = None
    is_working: bool

class WorkingScheduleUpdate(BaseModel):
    weekday: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    is_working: bool = True

    @field_validator("end_time")
    @classmethod
    def validate_times(cls, end_time: time, info) -> time:
        values = info.data
        start_time = values.get("start_time")
        if start_time and end_time <= start_time:
            raise ValueError("Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak")
        return end_time


# ── Blocked Time Schemas ──────────────────────────────────────────────────────
class BlockedTimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    barber_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    reason: str | None = None
    created_at: datetime

class BlockedTimeCreate(BaseModel):
    start_at: datetime = Field(..., description="Start of blocked period (UTC)")
    end_at: datetime = Field(..., description="End of blocked period (UTC)")
    reason: str | None = Field(None, max_length=500)

    @field_validator("end_at")
    @classmethod
    def validate_datetimes(cls, end_at: datetime, info) -> datetime:
        values = info.data
        start_at = values.get("start_at")
        if start_at and end_at <= start_at:
            raise ValueError("Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak")
        if end_at.tzinfo is None or end_at.utcoffset() is None:
            raise ValueError("Tugash vaqti vaqt mintaqasi bilan yuborilishi kerak")
        return end_at.astimezone(timezone.utc)

    @field_validator("start_at")
    @classmethod
    def validate_start_timezone(cls, start_at: datetime) -> datetime:
        if start_at.tzinfo is None or start_at.utcoffset() is None:
            raise ValueError("Boshlanish vaqti vaqt mintaqasi bilan yuborilishi kerak")
        return start_at.astimezone(timezone.utc)


class BlockedTimeUpdate(BlockedTimeCreate):
    """Full replacement of a barber-owned blocked time period."""
