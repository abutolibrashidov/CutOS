"""Location model — represents a shared physical barber shop."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDBase


class Location(TimestampMixin, UUIDBase):
    """
    A shared physical location where one or more independent barbers operate.

    This entity exists even in the single-shop prototype so that the
    architecture can later support multiple locations without a schema redesign.
    """

    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    barbers: Mapped[list["Barber"]] = relationship(  # noqa: F821
        "Barber", back_populates="location"
    )

    def __repr__(self) -> str:
        return f"<Location id={self.id} name={self.name!r}>"
