"""Customer appointment list and cancellation endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.customer_auth import CurrentCustomer
from app.core.database import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.customer import AppointmentResponse, CancelResponse, appointment_to_response

router = APIRouter(tags=["customer-appointments"])

CANCELLATION_CUTOFF_MINUTES = 60  # customer cannot cancel within 1 hour of appointment


@router.get("/", response_model=list[AppointmentResponse])
async def list_my_appointments(
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
) -> list[AppointmentResponse]:
    """Return the authenticated customer's appointments, most recent first."""
    stmt = (
        select(Appointment)
        .where(Appointment.customer_id == customer.id)
        .order_by(Appointment.start_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [appointment_to_response(r) for r in rows]


@router.post("/{appointment_id}/cancel", response_model=CancelResponse)
async def cancel_my_appointment(
    appointment_id: uuid.UUID,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
) -> CancelResponse:
    """
    Cancel a customer's own appointment.

    Policy: customer can cancel up to 1 hour before the start time.
    After that, cancellation is refused.
    """
    stmt = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.customer_id == customer.id,
    )
    appointment = (await db.execute(stmt)).scalars().first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buyurtma allaqachon bekor qilingan",
        )
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yakunlangan buyurtmani bekor qilib bo'lmaydi",
        )

    cutoff = appointment.start_at - timedelta(minutes=CANCELLATION_CUTOFF_MINUTES)
    now = datetime.now(timezone.utc)
    if now >= cutoff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buyurtmani bekor qilish muddati o'tdi. Boshlanishdan 1 soat oldin bekor qilish kerak.",
        )

    appointment.status = AppointmentStatus.CANCELLED
    await db.flush()
    await db.refresh(appointment)

    return CancelResponse(id=appointment.id, status=appointment.status.value)
