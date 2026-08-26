"""GET /api/v1/customer/barbers/{barber_id}/services/ — barber's active services."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.barber import Barber
from app.models.service import Service
from app.schemas.customer import ServicePublic

router = APIRouter(tags=["customer-services"])


@router.get("/{barber_id}/services/", response_model=list[ServicePublic])
async def list_barber_services(
    barber_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ServicePublic]:
    """Return active services for a specific barber. No authentication required."""
    # Verify barber exists and is active
    barber = (
        await db.execute(
            select(Barber).where(Barber.id == barber_id, Barber.is_active == True)  # noqa: E712
        )
    ).scalars().first()
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barber topilmadi")

    stmt = (
        select(Service)
        .where(Service.barber_id == barber_id, Service.is_active == True)  # noqa: E712
        .order_by(Service.name)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [ServicePublic.model_validate(r) for r in rows]
