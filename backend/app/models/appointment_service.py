"""AppointmentService — per-service snapshot rows for a multi-service appointment."""

import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDBase


class AppointmentService(UUIDBase):
    """
    One row per service included in an appointment.

    All monetary and duration values are FROZEN at booking time.
    Later edits to the Service record never affect these rows.

    Relationships:
      - appointment  : the parent Appointment
      - service      : the Service as it existed at booking time
                       (ondelete=RESTRICT so we cannot accidentally delete a
                       service that has historical records; barbers should
                       deactivate services instead)
    """

    __tablename__ = "appointment_services"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Snapshot — frozen at booking time
    service_name_at_booking: Mapped[str] = mapped_column(String(255), nullable=False)
    price_at_booking: Mapped[int] = mapped_column(BigInteger, nullable=False)   # integer UZS
    duration_at_booking: Mapped[int] = mapped_column(Integer, nullable=False)   # minutes

    # Relationships
    appointment: Mapped["Appointment"] = relationship(  # noqa: F821
        "Appointment", back_populates="appointment_services"
    )
    service: Mapped["Service"] = relationship(  # noqa: F821
        "Service", back_populates="appointment_service_rows"
    )

    def __repr__(self) -> str:
        return (
            f"<AppointmentService appointment={self.appointment_id} "
            f"service={self.service_id} price={self.price_at_booking}>"
        )
