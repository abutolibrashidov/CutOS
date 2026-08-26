"""GET /api/v1/customer/barbers/ — list active barbers at a location."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.barber import Barber
from app.schemas.customer import BarberPublic

router = APIRouter(tags=["customer-barbers"])


@router.get("/", response_model=list[BarberPublic])
async def list_barbers(
    location_id: uuid.UUID = Query(..., description="Filter barbers by location"),
    db: AsyncSession = Depends(get_db),
) -> list[BarberPublic]:
    """Return active barbers at the specified location. No authentication required."""
    stmt = (
        select(Barber)
        .where(Barber.location_id == location_id, Barber.is_active == True)  # noqa: E712
        .order_by(Barber.full_name)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [BarberPublic.model_validate(r) for r in rows]
