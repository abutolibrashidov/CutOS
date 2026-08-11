"""Barber model — an independent business user operating at a location."""

import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDBase


class Barber(TimestampMixin, UUIDBase):
    """
    An independent barber who manages their own services, schedule,
    appointments, customers, and finances.

    location_id is nullable to support future independent barbers who are
    not associated with any physical location.
    """

    __tablename__ = "barbers"

    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Telegram identity — the primary authentication mechanism
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    location: Mapped["Location | None"] = relationship(  # noqa: F821
        "Location", back_populates="barbers"
    )
    services: Mapped[list["Service"]] = relationship(  # noqa: F821
        "Service", back_populates="barber", cascade="all, delete-orphan"
    )
    working_schedules: Mapped[list["WorkingSchedule"]] = relationship(  # noqa: F821
        "WorkingSchedule", back_populates="barber", cascade="all, delete-orphan"
    )
    blocked_times: Mapped[list["BlockedTime"]] = relationship(  # noqa: F821
        "BlockedTime", back_populates="barber", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(  # noqa: F821
        "Appointment", back_populates="barber"
    )
    barber_customers: Mapped[list["BarberCustomer"]] = relationship(  # noqa: F821
        "BarberCustomer", back_populates="barber", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(  # noqa: F821
        "Expense", back_populates="barber", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Barber id={self.id} name={self.full_name!r}>"
