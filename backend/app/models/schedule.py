"""WorkingSchedule model — barber's regular weekly hours."""

import uuid
from datetime import time

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDBase


class WorkingSchedule(UUIDBase):
    """
    A barber's regular working hours for a specific day of the week.

    weekday follows Python's convention: 0=Monday, 6=Sunday.

    One row per weekday per barber. is_working=False means the barber
    does not work that day (used instead of deleting the row so the
    frontend can show a complete weekly grid).
    """

    __tablename__ = "working_schedules"
    __table_args__ = (
        UniqueConstraint("barber_id", "weekday", name="uq_barber_weekday"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_working_schedules_weekday"),
        CheckConstraint("end_time > start_time", name="ck_working_schedules_time_order"),
    )

    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 0 = Monday, 6 = Sunday
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_working: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    barber: Mapped["Barber"] = relationship(  # noqa: F821
        "Barber", back_populates="working_schedules"
    )

    def __repr__(self) -> str:
        return (
            f"<WorkingSchedule barber={self.barber_id} weekday={self.weekday} "
            f"{self.start_time}–{self.end_time} working={self.is_working}>"
        )
