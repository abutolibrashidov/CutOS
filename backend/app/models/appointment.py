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

    SNAPSHOT FIELDS (service_name_at_booking, price_at_booking, duration_at_booking):
    These are frozen copies of the service details at the moment of booking.
    Future edits to Service records NEVER affect historical appointments.

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
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
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

    # ── Snapshot fields ───────────────────────────────────────────────────────
    # Frozen at booking time — never changes even if the Service is later edited
    service_name_at_booking: Mapped[str] = mapped_column(String(255), nullable=False)
    price_at_booking: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # integer UZS
    duration_at_booking: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # minutes

    # Optional notes (barber or system)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    barber: Mapped["Barber"] = relationship(  # noqa: F821
        "Barber", back_populates="appointments"
    )
    customer: Mapped["Customer"] = relationship(  # noqa: F821
        "Customer", back_populates="appointments"
    )
    service: Mapped["Service"] = relationship(  # noqa: F821
        "Service", back_populates="appointments"
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment id={self.id} barber={self.barber_id} "
            f"status={self.status} start={self.start_at}>"
        )
