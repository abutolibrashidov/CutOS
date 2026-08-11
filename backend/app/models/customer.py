"""Customer model — shared identity record across the platform."""

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDBase


class Customer(TimestampMixin, UUIDBase):
    """
    A shared customer identity.

    One record per person across the entire platform — not per barber.
    Per-barber relationship data (visit counts, notes, spend) lives in
    BarberCustomer.

    telegram_id is nullable to support walk-in customers who have no
    Telegram account. Walk-ins are created by the barber manually.
    """

    __tablename__ = "customers"

    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Relationships
    barber_relationships: Mapped[list["BarberCustomer"]] = relationship(  # noqa: F821
        "BarberCustomer", back_populates="customer", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(  # noqa: F821
        "Appointment", back_populates="customer"
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.full_name!r}>"
