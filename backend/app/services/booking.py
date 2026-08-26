"""Atomic booking service — race-condition-safe appointment creation.

Uses a transaction-scoped advisory lock plus SELECT ... FOR UPDATE so two
simultaneous customers cannot book the same empty slot.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentSource, AppointmentStatus
from app.models.appointment_service import AppointmentService
from app.models.barber_customer import BarberCustomer
from app.models.service import Service
from app.services.availability import (
    acquire_booking_lock,
    is_aligned_slot,
    validate_slot,
)


async def _get_or_create_barber_customer(
    barber_id: uuid.UUID,
    customer_id: uuid.UUID,
    db: AsyncSession,
) -> BarberCustomer:
    """Upsert a BarberCustomer record. Called inside the booking transaction."""
    stmt = select(BarberCustomer).where(
        BarberCustomer.barber_id == barber_id,
        BarberCustomer.customer_id == customer_id,
    )
    bc = (await db.execute(stmt)).scalars().first()
    if bc is None:
        bc = BarberCustomer(barber_id=barber_id, customer_id=customer_id)
        db.add(bc)
    return bc


async def create_booking(
    *,
    barber_id: uuid.UUID,
    customer_id: uuid.UUID,
    service_ids: list[uuid.UUID],
    start_at: datetime,
    db: AsyncSession,
    source: AppointmentSource = AppointmentSource.ONLINE,
) -> Appointment:
    """
    Create an appointment atomically.

    Steps (all inside the caller's transaction):
    1. Load and verify all services belong to the barber and are active.
    2. Compute total duration and total price (server-side — never trust client).
    3. Validate the slot with SELECT FOR UPDATE (locks conflicting appointment rows).
    4. If conflict → raise HTTP 409.
    5. Insert Appointment row with aggregate price/duration.
    6. Insert one AppointmentService row per service.
    7. Upsert BarberCustomer record.
    8. Return the Appointment (caller commits).
    """
    if not service_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Kamida bitta xizmat tanlash kerak",
        )

    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    else:
        start_at = start_at.astimezone(timezone.utc)

    if not is_aligned_slot(start_at):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Boshlanish vaqti 15 daqiqalik oralig'ida bo'lishi kerak",
        )

    if start_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O'tgan vaqtga buyurtma berib bo'lmaydi",
        )

    # 1. Load services — verify ownership and active status
    svc_stmt = select(Service).where(
        Service.id.in_(service_ids),
        Service.barber_id == barber_id,
        Service.is_active == True,  # noqa: E712
    )
    svc_rows = (await db.execute(svc_stmt)).scalars().all()

    found_ids = {svc.id for svc in svc_rows}
    missing_ids = set(service_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ba'zi xizmatlar topilmadi yoki faol emas",
        )

    # 2. Compute totals server-side
    total_price = sum(svc.price_uzs for svc in svc_rows)
    total_duration = sum(svc.duration_minutes for svc in svc_rows)
    end_at = start_at + timedelta(minutes=total_duration)

    # 3. Serialize same-barber/day bookings, then validate with row locks
    await acquire_booking_lock(barber_id, start_at, db)
    slot_free = await validate_slot(barber_id, start_at, total_duration, db)
    if not slot_free:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu vaqt hozirgina band qilindi. Iltimos, boshqa vaqtni tanlang.",
        )

    # 4. Create the Appointment
    appointment = Appointment(
        barber_id=barber_id,
        customer_id=customer_id,
        start_at=start_at,
        end_at=end_at,
        status=AppointmentStatus.CONFIRMED,
        source=source,
        price_at_booking=total_price,
        duration_at_booking=total_duration,
        # service_id and service_name_at_booking intentionally NULL for multi-service rows
    )
    db.add(appointment)
    await db.flush()  # generates appointment.id

    # 5. Create per-service snapshot rows
    # Maintain insertion order to match service_ids order if needed
    svc_by_id = {svc.id: svc for svc in svc_rows}
    for sid in service_ids:
        svc = svc_by_id[sid]
        db.add(AppointmentService(
            appointment_id=appointment.id,
            service_id=svc.id,
            service_name_at_booking=svc.name,
            price_at_booking=svc.price_uzs,
            duration_at_booking=svc.duration_minutes,
        ))

    # 6. Upsert BarberCustomer
    await _get_or_create_barber_customer(barber_id, customer_id, db)

    return appointment
