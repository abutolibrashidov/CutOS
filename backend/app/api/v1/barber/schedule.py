from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentBarber
from app.core.database import get_db
from app.models.schedule import WorkingSchedule
from app.schemas.barber import WorkingScheduleResponse, WorkingScheduleUpdate

router = APIRouter()


@router.get("/", response_model=list[WorkingScheduleResponse])
async def get_schedule(
    barber: CurrentBarber,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkingScheduleResponse]:
    """
    Get the weekly schedule grid for the authenticated barber.

    Always returns a seven-day grid. Weekday index 0=Mon, 6=Sun.
    Days without stored hours are returned as OFF with null start/end times.
    """
    stmt = select(WorkingSchedule).where(WorkingSchedule.barber_id == barber.id).order_by(WorkingSchedule.weekday)
    result = await db.execute(stmt)
    schedules = {schedule.weekday: schedule for schedule in result.scalars().all()}
    return [
        schedules.get(
            weekday,
            WorkingScheduleResponse(
                barber_id=barber.id,
                weekday=weekday,
                start_time=None,
                end_time=None,
                is_working=False,
            ),
        )
        for weekday in range(7)
    ]


@router.post("/", response_model=list[WorkingScheduleResponse])
async def update_schedule(
    barber: CurrentBarber,
    payloads: list[WorkingScheduleUpdate],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkingScheduleResponse]:
    """
    Upsert weekly schedules for the barber (create or update days off & hours).

    Accepts an array of weekday settings to allow batch updates.
    """
    results = []

    for payload in payloads:
        # Construct PostgreSQL upsert
        insert_stmt = insert(WorkingSchedule).values(
            barber_id=barber.id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
            is_working=payload.is_working,
        )

        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_barber_weekday",
            set_={
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "is_working": payload.is_working,
            },
        ).returning(WorkingSchedule)

        res = await db.execute(upsert_stmt)
        # Flush each to populate the model row
        results.append(res.scalars().one())

    await db.flush()
    return results
