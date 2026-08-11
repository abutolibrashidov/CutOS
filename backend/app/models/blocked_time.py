"""BlockedTime model — one-off time blocks that prevent bookings."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDBase


class BlockedTime(TimestampMixin, UUIDBase):
    """
    A one-off time block set by a barber to prevent online bookings.

    Examples: personal errands, lunch, early departure, holiday.
    These override the regular WorkingSchedule for the overlapping window.

    All times stored in UTC.
    """

    __tablename__ = "blocked_times"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_blocked_times_time_order"),
    )

    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    barber: Mapped["Barber"] = relationship(  # noqa: F821
        "Barber", back_populates="blocked_times"
    )

    def __repr__(self) -> str:
        return (
            f"<BlockedTime barber={self.barber_id} {self.start_at}–{self.end_at}>"
        )
