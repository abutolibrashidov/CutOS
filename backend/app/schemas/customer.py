"""Customer-facing Pydantic schemas for Stage 3."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Location ────────────────────────────────────────────────────────────────

class LocationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    address: str | None = None
    city: str | None = None


# ── Barber (public view) ─────────────────────────────────────────────────────

class BarberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    bio: str | None = None
    avatar_url: str | None = None


# ── Service (public view) ────────────────────────────────────────────────────

class ServicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    price_uzs: int
    duration_minutes: int


# ── Availability ─────────────────────────────────────────────────────────────

class AvailabilityResponse(BaseModel):
    barber_id: uuid.UUID
    date: str  # YYYY-MM-DD
    slots: list[datetime]  # UTC datetimes


# ── Booking ──────────────────────────────────────────────────────────────────

class BookingRequest(BaseModel):
    location_id: uuid.UUID
    barber_id: uuid.UUID | None = Field(
        None,
        description="Specific barber. Leave null for 'any available barber'.",
    )
    service_ids: list[uuid.UUID] = Field(..., min_length=1)
    start_at: datetime = Field(..., description="Requested start time (UTC)")


class AppointmentServiceSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    service_id: uuid.UUID
    service_name_at_booking: str
    price_at_booking: int
    duration_at_booking: int


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    barber_id: uuid.UUID
    customer_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: str
    source: str
    price_at_booking: int
    duration_at_booking: int
    appointment_services: list[AppointmentServiceSnapshot] = []
    notes: str | None = None
    created_at: datetime
    customer_full_name: str | None = None
    customer_phone: str | None = None
    barber_full_name: str | None = None


def appointment_to_response(appointment: object) -> AppointmentResponse:
    """Build AppointmentResponse including related customer/barber display fields."""
    customer = getattr(appointment, "customer", None)
    barber = getattr(appointment, "barber", None)
    status_val = getattr(appointment, "status", None)
    source_val = getattr(appointment, "source", None)
    return AppointmentResponse(
        id=appointment.id,  # type: ignore[attr-defined]
        barber_id=appointment.barber_id,  # type: ignore[attr-defined]
        customer_id=appointment.customer_id,  # type: ignore[attr-defined]
        start_at=appointment.start_at,  # type: ignore[attr-defined]
        end_at=appointment.end_at,  # type: ignore[attr-defined]
        status=status_val.value if hasattr(status_val, "value") else str(status_val),
        source=source_val.value if hasattr(source_val, "value") else str(source_val),
        price_at_booking=appointment.price_at_booking,  # type: ignore[attr-defined]
        duration_at_booking=appointment.duration_at_booking,  # type: ignore[attr-defined]
        appointment_services=[
            AppointmentServiceSnapshot.model_validate(row)
            for row in getattr(appointment, "appointment_services", []) or []
        ],
        notes=getattr(appointment, "notes", None),
        created_at=appointment.created_at,  # type: ignore[attr-defined]
        customer_full_name=getattr(customer, "full_name", None) if customer else None,
        customer_phone=getattr(customer, "phone", None) if customer else None,
        barber_full_name=getattr(barber, "full_name", None) if barber else None,
    )


class BookingResponse(BaseModel):
    appointment: AppointmentResponse
    barber: BarberPublic
    services: list[AppointmentServiceSnapshot]
    total_price_uzs: int
    total_duration_minutes: int


# ── Cancellation ──────────────────────────────────────────────────────────────

class CancelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    message: str = "Buyurtma bekor qilindi."


# ── Walk-in ───────────────────────────────────────────────────────────────────

class WalkInRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=30)
    service_ids: list[uuid.UUID] = Field(..., min_length=1)
    start_at: datetime = Field(..., description="Appointment start time (UTC)")
