import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentBarber
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.service import Service
from app.schemas.barber import ServiceCreate, ServiceResponse, ServiceUpdate

router = APIRouter()


@router.get("/", response_model=list[ServiceResponse])
async def list_services(
    barber: CurrentBarber,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ServiceResponse]:
    """List all services offered by the authenticated barber."""
    stmt = select(Service).where(Service.barber_id == barber.id).order_by(Service.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    barber: CurrentBarber,
    payload: ServiceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ServiceResponse:
    """Create a new service for the authenticated barber."""
    service = Service(
        barber_id=barber.id,
        name=payload.name,
        price_uzs=payload.price_uzs,
        duration_minutes=payload.duration_minutes,
        is_active=True,
    )
    db.add(service)
    await db.flush()
    return service


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: uuid.UUID,
    barber: CurrentBarber,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ServiceResponse:
    """Get details of a specific service owned by the authenticated barber."""
    stmt = select(Service).where(Service.id == service_id, Service.barber_id == barber.id)
    result = await db.execute(stmt)
    service = result.scalars().first()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Xizmat topilmadi",
        )
    return service


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: uuid.UUID,
    barber: CurrentBarber,
    payload: ServiceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ServiceResponse:
    """Update service configurations (price, duration, status, etc.)."""
    stmt = select(Service).where(Service.id == service_id, Service.barber_id == barber.id)
    result = await db.execute(stmt)
    service = result.scalars().first()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Xizmat topilmadi",
        )

    if payload.name is not None:
        service.name = payload.name
    if payload.price_uzs is not None:
        service.price_uzs = payload.price_uzs
    if payload.duration_minutes is not None:
        service.duration_minutes = payload.duration_minutes
    if payload.is_active is not None:
        service.is_active = payload.is_active

    db.add(service)
    await db.flush()
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: uuid.UUID,
    barber: CurrentBarber,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a service.

    Raises HTTP 400 Bad Request if the service is already referenced by historical
    or future appointments. Recommends deactivation instead.
    """
    # 1. Fetch service to ensure it exists and belongs to the barber
    stmt = select(Service).where(Service.id == service_id, Service.barber_id == barber.id)
    result = await db.execute(stmt)
    service = result.scalars().first()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Xizmat topilmadi",
        )

    # 2. Check if referenced by any appointments
    appt_stmt = select(Appointment.id).where(Appointment.service_id == service_id).limit(1)
    appt_result = await db.execute(appt_stmt)
    has_appointments = appt_result.scalars().first() is not None

    if has_appointments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ushbu xizmatni o'chirib bo'lmaydi, chunki unda buyurtmalar bor. Buning o'rniga uni faolsizlantirishingiz mumkin.",
        )

    # 3. Hard delete is safe
    await db.delete(service)
    await db.flush()
