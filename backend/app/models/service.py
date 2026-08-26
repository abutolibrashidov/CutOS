"""Service model — a service offered by a specific barber."""

import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDBase


class Service(TimestampMixin, UUIDBase):
    """
    A service offered by a barber.

    Services belong exclusively to individual barbers.
    There is NO shared global service list — each barber sets:
    - Their own service names
    - Their own prices (integer UZS)
    - Their own durations
    """

    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("price_uzs >= 0", name="ck_services_price_nonnegative"),
        CheckConstraint("duration_minutes > 0", name="ck_services_duration_positive"),
    )

    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Integer UZS — no floating-point for money
    price_uzs: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    barber: Mapped["Barber"] = relationship(  # noqa: F821
        "Barber", back_populates="services"
    )
    appointments: Mapped[list["Appointment"]] = relationship(  # noqa: F821
        "Appointment", back_populates="service"
    )
    appointment_service_rows: Mapped[list["AppointmentService"]] = relationship(  # noqa: F821
        "AppointmentService", back_populates="service"
    )

    def __repr__(self) -> str:
        return (
            f"<Service id={self.id} name={self.name!r} "
            f"price={self.price_uzs} duration={self.duration_minutes}min>"
        )
