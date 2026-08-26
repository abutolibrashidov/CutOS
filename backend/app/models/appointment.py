"""Appointment model — a booked or walk-in session with snapshot fields."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDBase


class AppointmentStatus(str, enum.Enum):
    """Lifecycle states of an appointment."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentSource(str, enum.Enum):
    """How the appointment was created."""

    ONLINE = "online"    # customer booked via Mini App
    WALKIN = "walkin"    # barber added manually


class Appointment(TimestampMixin, UUIDBase):
    """
    A single appointment session.

    MULTI-SERVICE SUPPORT (Stage 3):
    Detailed per-service snapshots live in AppointmentService (one row per
    service included in the booking).  The aggregate totals are kept here
    for efficient overlap queries:
      - price_at_booking  : sum of all AppointmentService.price_at_booking
      - duration_at_booking : sum of all AppointmentService.duration_at_booking

    LEGACY SINGLE-SERVICE FIELD:
    service_id and service_name_at_booking are now nullable so that existing
    Stage-2 test data and historical rows are not broken.  New bookings
    created via the Stage-3 API leave these NULL and use the
    appointment_services join table instead.

    end_at is derived from start_at + duration_at_booking and stored explicitly
    for efficient overlap queries during availability calculation.

    price_at_booking is stored as integer UZS — no floating-point.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_appointments_time_order"),
        CheckConstraint("price_at_booking >= 0", name="ck_appointments_price_nonnegative"),
        CheckConstraint("duration_at_booking > 0", name="ck_appointments_duration_positive"),
    )

    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Nullable from Stage 3 onward — multi-service bookings use appointment_services.
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Scheduling
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Status & source
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"),
        nullable=False,
        default=AppointmentStatus.CONFIRMED,
    )
    source: Mapped[AppointmentSource] = mapped_column(
        Enum(AppointmentSource, name="appointment_source"),
        nullable=False,
        default=AppointmentSource.ONLINE,
    )

    # ── Aggregate snapshot fields ──────────────────────────────────────────────
    # For multi-service bookings these are the SUM of all AppointmentService rows.
    # For legacy single-service rows they equal that one service's values.
    service_name_at_booking: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # NULL for multi-service bookings
    price_at_booking: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # total, integer UZS
    duration_at_booking: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # total minutes

    # Optional notes (barber or system)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    barber: Mapped["Barber"] = relationship(  # noqa: F821
        "Barber", back_populates="appointments", lazy="selectin"
    )
    customer: Mapped["Customer"] = relationship(  # noqa: F821
        "Customer", back_populates="appointments", lazy="selectin"
    )
    service: Mapped["Service | None"] = relationship(  # noqa: F821
        "Service", back_populates="appointments"
    )
    appointment_services: Mapped[list["AppointmentService"]] = relationship(  # noqa: F821
        "AppointmentService", back_populates="appointment", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment id={self.id} barber={self.barber_id} "
            f"status={self.status} start={self.start_at}>"
        )
