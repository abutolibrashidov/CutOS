"""Availability engine — computes open booking slots for a barber.

All datetime inputs and outputs are UTC-aware.
This module contains only pure async DB queries — no HTTP logic.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus
from app.models.barber import Barber
from app.models.blocked_time import BlockedTime
from app.models.schedule import WorkingSchedule

# Slot granularity in minutes (as specified in the architecture)
SLOT_MINUTES = 15


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Return True if [a_start, a_end) overlaps [b_start, b_end)."""
    return a_start < b_end and a_end > b_start


async def get_available_slots(
    barber_id: uuid.UUID,
    target_date: date,
    total_minutes: int,
    db: AsyncSession,
) -> list[datetime]:
    """
    Return a list of available UTC slot start-times for the given barber,
    date, and total appointment duration.

    Algorithm:
    1. Look up WorkingSchedule for target weekday.
    2. If not working → return [].
    3. Generate 15-min slot candidates from start_time to end_time - total_minutes.
    4. Load BlockedTime rows that touch the date window.
    5. Load active Appointment rows that touch the date window.
    6. Remove any candidate slot whose [slot, slot+total_minutes) overlaps a blocker.
    7. Return remaining slots.
    """
    weekday = target_date.weekday()  # 0=Monday, 6=Sunday

    # 1. Working schedule for that weekday
    schedule_stmt = select(WorkingSchedule).where(
        WorkingSchedule.barber_id == barber_id,
        WorkingSchedule.weekday == weekday,
        WorkingSchedule.is_working == True,  # noqa: E712
    )
    sched_row = (await db.execute(schedule_stmt)).scalars().first()
    if sched_row is None:
        return []

    # Build window boundaries as UTC datetimes (schedules stored as naive time,
    # treated as UTC-aligned local shop time for this prototype)
    day_start = datetime(
        target_date.year, target_date.month, target_date.day,
        sched_row.start_time.hour, sched_row.start_time.minute,
        tzinfo=timezone.utc,
    )
    day_end = datetime(
        target_date.year, target_date.month, target_date.day,
        sched_row.end_time.hour, sched_row.end_time.minute,
        tzinfo=timezone.utc,
    )

    # 2. Validate that the service can fit at all
    if total_minutes <= 0 or day_end <= day_start:
        return []

    # 3. Generate candidate slots
    duration = timedelta(minutes=total_minutes)
    slot_step = timedelta(minutes=SLOT_MINUTES)
    candidates: list[datetime] = []
    cursor = day_start
    while cursor + duration <= day_end:
        candidates.append(cursor)
        cursor += slot_step

    if not candidates:
        return []

    # 4. Load blocked times overlapping today's window
    blocked_stmt = select(BlockedTime).where(
        BlockedTime.barber_id == barber_id,
        BlockedTime.start_at < day_end,
        BlockedTime.end_at > day_start,
    )
    blocked_rows = (await db.execute(blocked_stmt)).scalars().all()

    # 5. Load active appointments overlapping today's window
    active_statuses = [
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.PENDING,
    ]
    apt_stmt = select(Appointment).where(
        Appointment.barber_id == barber_id,
        Appointment.status.in_(active_statuses),
        Appointment.start_at < day_end,
        Appointment.end_at > day_start,
    )
    apt_rows = (await db.execute(apt_stmt)).scalars().all()

    # 6. Build a combined list of blocked intervals
    blockers: list[tuple[datetime, datetime]] = (
        [(b.start_at, b.end_at) for b in blocked_rows]
        + [(a.start_at, a.end_at) for a in apt_rows]
    )

    # 7. Filter candidates (skip past slots and overlapping blockers)
    now = datetime.now(timezone.utc)
    available = []
    for slot_start in candidates:
        if slot_start <= now:
            continue
        slot_end = slot_start + duration
        if not any(_overlaps(slot_start, slot_end, bs, be) for bs, be in blockers):
            available.append(slot_start)

    return available


def is_aligned_slot(start_at: datetime) -> bool:
    """Return True if start_at falls on a 15-minute boundary with zero seconds."""
    return (
        start_at.minute % SLOT_MINUTES == 0
        and start_at.second == 0
        and start_at.microsecond == 0
    )


async def acquire_booking_lock(
    barber_id: uuid.UUID,
    start_at: datetime,
    db: AsyncSession,
) -> None:
    """
    Serialize bookings for the same barber + calendar day.

    SELECT FOR UPDATE alone cannot prevent double-booking an empty slot
    because there is no row to lock. A transaction-scoped advisory lock
    closes that race.
    """
    from sqlalchemy import text

    lock_key = f"booking:{barber_id}:{start_at.date().isoformat()}"
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": lock_key},
    )


async def validate_slot(
    barber_id: uuid.UUID,
    start_at: datetime,
    total_minutes: int,
    db: AsyncSession,
    exclude_appointment_id: uuid.UUID | None = None,
) -> bool:
    """
    Re-validate a specific slot inside a booking transaction.

    Returns True if the slot is free, False if it conflicts with an
    existing appointment or blocked time.

    exclude_appointment_id is used when rescheduling an existing appointment
    so it does not conflict with itself.
    """
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    else:
        start_at = start_at.astimezone(timezone.utc)

    end_at = start_at + timedelta(minutes=total_minutes)

    candidate_date = start_at.date()
    weekday = candidate_date.weekday()

    # Check working schedule
    sched_stmt = select(WorkingSchedule).where(
        WorkingSchedule.barber_id == barber_id,
        WorkingSchedule.weekday == weekday,
        WorkingSchedule.is_working == True,  # noqa: E712
    )
    sched_row = (await db.execute(sched_stmt)).scalars().first()
    if sched_row is None:
        return False

    day_start = datetime(
        candidate_date.year, candidate_date.month, candidate_date.day,
        sched_row.start_time.hour, sched_row.start_time.minute,
        tzinfo=timezone.utc,
    )
    day_end = datetime(
        candidate_date.year, candidate_date.month, candidate_date.day,
        sched_row.end_time.hour, sched_row.end_time.minute,
        tzinfo=timezone.utc,
    )

    # Slot must fit inside working hours
    if start_at < day_start or end_at > day_end:
        return False

    # Check blocked times
    blocked_stmt = select(BlockedTime).where(
        BlockedTime.barber_id == barber_id,
        BlockedTime.start_at < end_at,
        BlockedTime.end_at > start_at,
    )
    if (await db.execute(blocked_stmt)).scalars().first():
        return False

    # Check existing active appointments (with SELECT FOR UPDATE to lock rows)
    active_statuses = [AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]
    conflict_stmt = (
        select(Appointment)
        .where(
            Appointment.barber_id == barber_id,
            Appointment.status.in_(active_statuses),
            Appointment.start_at < end_at,
            Appointment.end_at > start_at,
        )
        .with_for_update(skip_locked=False)
    )
    if exclude_appointment_id:
        conflict_stmt = conflict_stmt.where(Appointment.id != exclude_appointment_id)

    if (await db.execute(conflict_stmt)).scalars().first():
        return False

    return True


async def map_services_to_barber(
    barber_id: uuid.UUID,
    reference_service_ids: list[uuid.UUID],
    db: AsyncSession,
) -> list[uuid.UUID] | None:
    """
    Map a list of reference service IDs (from another barber) to the matching
    active services of target barber (by name, case-insensitively, stripped).

    Returns a list of matching service IDs or None if the target barber
    does not offer all requested services.
    """
    from app.models.service import Service

    ref_svc_stmt = select(Service).where(Service.id.in_(reference_service_ids))
    ref_svcs = (await db.execute(ref_svc_stmt)).scalars().all()
    ref_names = [s.name.strip().lower() for s in ref_svcs]
    if len(ref_svcs) != len(reference_service_ids):
        return None

    barber_stmt = select(Service).where(
        Service.barber_id == barber_id,
        Service.is_active == True,  # noqa: E712
    )
    barber_svcs = (await db.execute(barber_stmt)).scalars().all()

    mapped_ids = []
    for name in ref_names:
        match = next((s for s in barber_svcs if s.name.strip().lower() == name), None)
        if match is None:
            return None
        mapped_ids.append(match.id)
    return mapped_ids


async def find_available_barber(
    location_id: uuid.UUID,
    service_ids: list[uuid.UUID],
    start_at: datetime,
    db: AsyncSession,
) -> Barber | None:
    """
    Find the first available barber at the given location for the requested slot.

    Selection rule: alphabetical by full_name (deterministic, documented).
    Services are mapped by name case-insensitively.
    """
    # Load active barbers at the location, sorted alphabetically
    barbers_stmt = (
        select(Barber)
        .where(
            Barber.location_id == location_id,
            Barber.is_active == True,  # noqa: E712
        )
        .order_by(Barber.full_name)
    )
    barbers = (await db.execute(barbers_stmt)).scalars().all()

    for barber in barbers:
        mapped_ids = await map_services_to_barber(barber.id, service_ids, db)
        if mapped_ids is None:
            continue

        # Load mapped services to calculate duration for this specific barber
        from app.models.service import Service
        svc_stmt = select(Service).where(Service.id.in_(mapped_ids))
        svc_rows = (await db.execute(svc_stmt)).scalars().all()
        barber_total_minutes = sum(s.duration_minutes for s in svc_rows)

        if await validate_slot(barber.id, start_at, barber_total_minutes, db):
            return barber

    return None
