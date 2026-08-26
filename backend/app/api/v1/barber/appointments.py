"""Barber-side appointment management: list, cancel, and walk-in creation.

These routes are protected by barber authentication. Barbers can only
see and manage their own appointments.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentBarber
from app.core.database import get_db
from app.models.appointment import Appointment, AppointmentSource, AppointmentStatus
from app.models.customer import Customer
from app.schemas.customer import AppointmentResponse, WalkInRequest, appointment_to_response
from app.services.booking import create_booking

router = APIRouter(tags=["barber-appointments"])


@router.get("/", response_model=list[AppointmentResponse])
async def list_barber_appointments(
    barber: CurrentBarber,
    db: AsyncSession = Depends(get_db),
) -> list[AppointmentResponse]:
    """Return the authenticated barber's appointments, most recent first."""
    stmt = (
        select(Appointment)
        .where(Appointment.barber_id == barber.id)
        .order_by(Appointment.start_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [appointment_to_response(r) for r in rows]


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def barber_cancel_appointment(
    appointment_id: uuid.UUID,
    barber: CurrentBarber,
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    """
    Barber cancels one of their own appointments.

    No cutoff restriction — barbers can cancel at any time.
    """
    stmt = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.barber_id == barber.id,
    )
    appointment = (await db.execute(stmt)).scalars().first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")

    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu buyurtma allaqachon yakunlangan yoki bekor qilingan",
        )

    appointment.status = AppointmentStatus.CANCELLED
    await db.flush()
    await db.refresh(appointment)
    return appointment_to_response(appointment)


@router.post("/walk-in/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_walk_in_appointment(
    payload: WalkInRequest,
    barber: CurrentBarber,
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    """
    Barber creates a walk-in appointment for a customer arriving in person.

    The customer may not have Telegram. A Customer record is created (or
    reused if phone matches an existing walk-in customer). Source = walkin.
    """
    # Find or create walk-in customer.
    # Walk-ins have no telegram_id. Match by phone if provided; otherwise always create new.
    customer: Customer | None = None
    if payload.phone:
        existing_stmt = select(Customer).where(
            Customer.phone == payload.phone,
            Customer.telegram_id.is_(None),
        )
        customer = (await db.execute(existing_stmt)).scalars().first()

    if customer is None:
        customer = Customer(
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            telegram_id=None,
        )
        db.add(customer)
        await db.flush()
    else:
        customer.full_name = payload.full_name.strip()

    appointment = await create_booking(
        barber_id=barber.id,
        customer_id=customer.id,
        service_ids=payload.service_ids,
        start_at=payload.start_at,
        db=db,
        source=AppointmentSource.WALKIN,
    )
    await db.flush()
    await db.refresh(appointment)
    return appointment_to_response(appointment)
