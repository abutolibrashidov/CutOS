"""GET /api/v1/customer/barbers/{barber_id}/available-slots/ — available time slots."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.barber import Barber
from app.models.service import Service
from app.schemas.customer import AvailabilityResponse
from app.services.availability import get_available_slots

router = APIRouter(tags=["customer-availability"])


@router.get("/{barber_id}/available-slots/", response_model=AvailabilityResponse)
async def get_barber_available_slots(
    barber_id: uuid.UUID,
    service_ids: list[uuid.UUID] = Query(..., description="Service IDs to include in total duration"),
    target_date: date = Query(..., alias="date", description="Date in YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    """
    Return available 15-minute slots for a specific barber on a given date.

    Total duration is computed from the requested services — the backend never
    trusts a client-supplied duration value.
    """
    # Verify barber exists and is active
    barber = (
        await db.execute(
            select(Barber).where(Barber.id == barber_id, Barber.is_active == True)  # noqa: E712
        )
    ).scalars().first()
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barber topilmadi")

    # Compute total duration from requested services (server-side)
    svc_stmt = select(Service).where(
        Service.id.in_(service_ids),
        Service.barber_id == barber_id,
        Service.is_active == True,  # noqa: E712
    )
    services = (await db.execute(svc_stmt)).scalars().all()
    if len(services) != len(service_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ba'zi xizmatlar topilmadi yoki faol emas",
        )

    total_minutes = sum(s.duration_minutes for s in services)

    slots = await get_available_slots(barber_id, target_date, total_minutes, db)

    return AvailabilityResponse(
        barber_id=barber_id,
        date=target_date.isoformat(),
        slots=slots,
    )
