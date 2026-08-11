"""Expense model — manually recorded expense by a barber."""

import uuid
from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDBase


class Expense(TimestampMixin, UUIDBase):
    """
    A manually recorded business expense by a barber.

    amount_uzs is stored as integer UZS — no floating-point.
    expense_date is a plain date (not timestamptz) since expenses
    are recorded per calendar day, not at a specific time.
    """

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount_uzs >= 0", name="ck_expenses_amount_nonnegative"),
    )

    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount_uzs: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # integer UZS
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # equipment | products | rent | other
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Relationships
    barber: Mapped["Barber"] = relationship(  # noqa: F821
        "Barber", back_populates="expenses"
    )

    def __repr__(self) -> str:
        return (
            f"<Expense barber={self.barber_id} amount={self.amount_uzs} UZS "
            f"date={self.expense_date}>"
        )
