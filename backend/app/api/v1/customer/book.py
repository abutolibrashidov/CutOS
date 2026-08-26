"""POST /api/v1/customer/book/ — atomic appointment booking."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.customer_auth import CurrentCustomer
from app.core.database import get_db
from app.models.barber import Barber
from app.models.appointment_service import AppointmentService
from app.schemas.customer import (
    AppointmentServiceSnapshot,
    BarberPublic,
    BookingRequest,
    BookingResponse,
    appointment_to_response,
)
from app.services.availability import find_available_barber, map_services_to_barber
from app.services.booking import create_booking
from app.models.appointment import AppointmentSource

router = APIRouter(tags=["customer-booking"])


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    payload: BookingRequest,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """
    Create an appointment atomically.

    If barber_id is null → "any available barber" is assigned alphabetically.
    The backend computes all prices and durations — never trusts the frontend.
    Returns the full booking details including assigned barber.
    """
    if payload.barber_id is None:
        assigned_barber = await find_available_barber(
            location_id=payload.location_id,
            service_ids=payload.service_ids,
            start_at=payload.start_at,
            db=db,
        )
        if assigned_barber is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu vaqtda hech qanday usta bo'sh emas. Boshqa vaqt tanlang.",
            )
        barber_id = assigned_barber.id
        mapped_ids = await map_services_to_barber(barber_id, payload.service_ids, db)
        if not mapped_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Xizmatlar mos kelmadi",
            )
        actual_service_ids = mapped_ids
    else:
        # Specific barber flow — validate barber exists and is at the location
        result = await db.execute(
            select(Barber).where(
                Barber.id == payload.barber_id,
                Barber.location_id == payload.location_id,
                Barber.is_active == True,  # noqa: E712
            )
        )
        assigned_barber = result.scalars().first()
        if not assigned_barber:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barber topilmadi",
            )
        barber_id = assigned_barber.id
        actual_service_ids = payload.service_ids

    # create_booking handles slot validation with SELECT FOR UPDATE (race-condition safe)
    appointment = await create_booking(
        barber_id=barber_id,
        customer_id=customer.id,
        service_ids=actual_service_ids,
        start_at=payload.start_at,
        db=db,
        source=AppointmentSource.ONLINE,
    )
    await db.flush()
    await db.refresh(appointment)

    # Load service snapshots for the response
    svc_rows = (
        await db.execute(
            select(AppointmentService).where(
                AppointmentService.appointment_id == appointment.id
            )
        )
    ).scalars().all()

    services_out = [AppointmentServiceSnapshot.model_validate(r) for r in svc_rows]

    return BookingResponse(
        appointment=appointment_to_response(appointment),
        barber=BarberPublic.model_validate(assigned_barber),
        services=services_out,
        total_price_uzs=appointment.price_at_booking,
        total_duration_minutes=appointment.duration_at_booking,
    )
