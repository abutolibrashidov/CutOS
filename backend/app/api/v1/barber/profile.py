from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentBarber
from app.core.database import get_db
from app.schemas.barber import BarberProfileResponse, BarberProfileUpdate

router = APIRouter()


@router.get("/profile", response_model=BarberProfileResponse)
async def get_profile(
    barber: CurrentBarber,
) -> BarberProfileResponse:
    """Fetch the authenticated barber's profile information."""
    return barber


@router.put("/profile", response_model=BarberProfileResponse)
async def update_profile(
    barber: CurrentBarber,
    payload: BarberProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BarberProfileResponse:
    """Update the authenticated barber's profile details."""
    barber.full_name = payload.full_name
    barber.phone = payload.phone
    barber.bio = payload.bio
    barber.avatar_url = payload.avatar_url

    db.add(barber)
    # The session committing/flushing is handled by the get_db dependency generator,
    # but we can call flush here to ensure values are refreshed
    await db.flush()
    return barber
