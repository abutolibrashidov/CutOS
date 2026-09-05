"""Admin API endpoints for Location management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate

router = APIRouter(prefix="/locations", tags=["admin-locations"])


@router.get("/", response_model=list[LocationResponse])
async def list_locations(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[LocationResponse]:
    """List all locations for admin management."""
    stmt = select(Location).order_by(Location.name.asc())
    result = await db.execute(stmt)
    locations = result.scalars().all()
    return locations


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LocationResponse:
    """Get single location details by ID."""
    stmt = select(Location).where(Location.id == location_id)
    loc = (await db.execute(stmt)).scalars().first()
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Joylashuv topilmadi",
        )
    return loc


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    payload: LocationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LocationResponse:
    """Create a new physical shop location."""
    new_loc = Location(
        name=payload.name,
        address=payload.address,
        city=payload.city,
        is_active=payload.is_active,
    )
    db.add(new_loc)
    await db.commit()
    await db.refresh(new_loc)
    return new_loc


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: uuid.UUID,
    payload: LocationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LocationResponse:
    """Update location information."""
    stmt = select(Location).where(Location.id == location_id)
    loc = (await db.execute(stmt)).scalars().first()
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Joylashuv topilmadi",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(loc, field, val)

    await db.commit()
    await db.refresh(loc)
    return loc
