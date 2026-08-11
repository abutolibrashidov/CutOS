import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentBarber
from app.core.database import get_db
from app.models.blocked_time import BlockedTime
from app.schemas.barber import BlockedTimeCreate, BlockedTimeResponse, BlockedTimeUpdate

router = APIRouter()


@router.get("/", response_model=list[BlockedTimeResponse])
async def list_blocked_times(
    barber: CurrentBarber,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BlockedTimeResponse]:
    """Retrieve all blocked time periods for the authenticated barber."""
    stmt = (
        select(BlockedTime)
        .where(BlockedTime.barber_id == barber.id)
        .order_by(BlockedTime.start_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=BlockedTimeResponse, status_code=status.HTTP_201_CREATED)
async def create_blocked_time(
    barber: CurrentBarber,
    payload: BlockedTimeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BlockedTimeResponse:
    """Create a new blocked time period for the authenticated barber."""
    blocked_time = BlockedTime(
        barber_id=barber.id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        reason=payload.reason,
    )
    db.add(blocked_time)
    await db.flush()
    return blocked_time


@router.put("/{blocked_time_id}", response_model=BlockedTimeResponse)
async def update_blocked_time(
    blocked_time_id: uuid.UUID,
    barber: CurrentBarber,
    payload: BlockedTimeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BlockedTimeResponse:
    """Replace a blocked time period owned by the authenticated barber."""
    stmt = select(BlockedTime).where(
        BlockedTime.id == blocked_time_id,
        BlockedTime.barber_id == barber.id,
    )
    result = await db.execute(stmt)
    blocked_time = result.scalars().first()

    if not blocked_time:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="To'siq vaqti topilmadi",
        )

    blocked_time.start_at = payload.start_at
    blocked_time.end_at = payload.end_at
    blocked_time.reason = payload.reason
    await db.flush()
    return blocked_time


@router.delete("/{blocked_time_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blocked_time(
    blocked_time_id: uuid.UUID,
    barber: CurrentBarber,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a specific blocked time period owned by the authenticated barber."""
    stmt = select(BlockedTime).where(
        BlockedTime.id == blocked_time_id,
        BlockedTime.barber_id == barber.id,
    )
    result = await db.execute(stmt)
    blocked_time = result.scalars().first()

    if not blocked_time:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="To'siq vaqti topilmadi",
        )

    await db.delete(blocked_time)
    await db.flush()
