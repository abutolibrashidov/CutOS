"""BarberCustomer — per-barber relationship record for a customer."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDBase


class BarberCustomer(UUIDBase):
    """
    Junction table that represents the relationship between a specific barber
    and a customer.

    This is the data-isolation boundary:
    - total_visits, total_spent_uzs, last_visit_at, notes all belong to THIS barber.
    - Barber A cannot see Barber B's BarberCustomer record for the same customer.

    Upserted when a barber first serves a customer.
    Updated when an appointment is marked completed.
    """

    __tablename__ = "barber_customers"
    __table_args__ = (
        UniqueConstraint("barber_id", "customer_id", name="uq_barber_customer"),
    )

    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stats — updated when appointments are completed
    total_visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent_uzs: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )  # integer UZS, no floats
    first_visit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_visit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Barber-private notes about this customer
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    barber: Mapped["Barber"] = relationship(  # noqa: F821
        "Barber", back_populates="barber_customers"
    )
    customer: Mapped["Customer"] = relationship(  # noqa: F821
        "Customer", back_populates="barber_relationships"
    )

    def __repr__(self) -> str:
        return (
            f"<BarberCustomer barber={self.barber_id} customer={self.customer_id} "
            f"visits={self.total_visits}>"
        )
