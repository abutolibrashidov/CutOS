"""Admin API routes for Barber management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.barber import Barber
from app.models.location import Location
from app.schemas.admin import (
    AdminBarberCreate,
    AdminBarberResponse,
    AdminBarberStatusUpdate,
    AdminBarberUpdate,
)

router = APIRouter(prefix="/barbers", tags=["admin-barbers"])


@router.get("/", response_model=list[AdminBarberResponse])
async def list_barbers(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminBarberResponse]:
    """List all barbers for admin management."""
    stmt = (
        select(Barber, Location.name.label("location_name"))
        .outerjoin(Location, Barber.location_id == Location.id)
        .order_by(Barber.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    response_list: list[AdminBarberResponse] = []
    for barber, loc_name in rows:
        resp = AdminBarberResponse.model_validate(barber)
        resp.location_name = loc_name
        response_list.append(resp)

    return response_list


@router.get("/{barber_id}", response_model=AdminBarberResponse)
async def get_barber(
    barber_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBarberResponse:
    """Get single barber details by ID."""
    stmt = (
        select(Barber, Location.name.label("location_name"))
        .outerjoin(Location, Barber.location_id == Location.id)
        .where(Barber.id == barber_id)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barber topilmadi",
        )

    barber, loc_name = row
    resp = AdminBarberResponse.model_validate(barber)
    resp.location_name = loc_name
    return resp


@router.post("/", response_model=AdminBarberResponse, status_code=status.HTTP_201_CREATED)
async def create_barber(
    payload: AdminBarberCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBarberResponse:
    """Provision a new barber with a unique Telegram ID."""
    # 1. Check for duplicate telegram_id
    existing_stmt = select(Barber).where(Barber.telegram_id == payload.telegram_id)
    existing = (await db.execute(existing_stmt)).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ushbu Telegram ID bilan allaqachon barber ro'yxatdan o'tgan",
        )

    # 2. Check location existence if location_id is provided
    loc_name: str | None = None
    if payload.location_id:
        loc_stmt = select(Location).where(Location.id == payload.location_id)
        loc = (await db.execute(loc_stmt)).scalars().first()
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ko'rsatilgan joylashuv topilmadi",
            )
        loc_name = loc.name

    # 3. Create Barber
    new_barber = Barber(
        telegram_id=payload.telegram_id,
        full_name=payload.full_name,
        phone=payload.phone,
        location_id=payload.location_id,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
        is_active=payload.is_active,
    )
    db.add(new_barber)
    await db.commit()
    await db.refresh(new_barber)

    resp = AdminBarberResponse.model_validate(new_barber)
    resp.location_name = loc_name
    return resp


@router.put("/{barber_id}", response_model=AdminBarberResponse)
async def update_barber(
    barber_id: uuid.UUID,
    payload: AdminBarberUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBarberResponse:
    """Update existing barber administrative information."""
    stmt = select(Barber).where(Barber.id == barber_id)
    barber = (await db.execute(stmt)).scalars().first()
    if not barber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barber topilmadi",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "location_id" in update_data and update_data["location_id"] is not None:
        loc_stmt = select(Location).where(Location.id == update_data["location_id"])
        loc = (await db.execute(loc_stmt)).scalars().first()
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ko'rsatilgan joylashuv topilmadi",
            )

    for field, val in update_data.items():
        setattr(barber, field, val)

    await db.commit()
    await db.refresh(barber)

    loc_name: str | None = None
    if barber.location_id:
        loc_stmt = select(Location.name).where(Location.id == barber.location_id)
        loc_name = (await db.execute(loc_stmt)).scalars().first()

    resp = AdminBarberResponse.model_validate(barber)
    resp.location_name = loc_name
    return resp


@router.patch("/{barber_id}/status", response_model=AdminBarberResponse)
async def toggle_barber_status(
    barber_id: uuid.UUID,
    payload: AdminBarberStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminBarberResponse:
    """Activate or deactivate a barber."""
    stmt = select(Barber).where(Barber.id == barber_id)
    barber = (await db.execute(stmt)).scalars().first()
    if not barber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barber topilmadi",
        )

    barber.is_active = payload.is_active
    await db.commit()
    await db.refresh(barber)

    loc_name: str | None = None
    if barber.location_id:
        loc_stmt = select(Location.name).where(Location.id == barber.location_id)
        loc_name = (await db.execute(loc_stmt)).scalars().first()

    resp = AdminBarberResponse.model_validate(barber)
    resp.location_name = loc_name
    return resp
