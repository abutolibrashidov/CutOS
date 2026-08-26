"""Customer authentication — same Telegram HMAC flow as barber auth.

Resolves or creates a Customer record from the verified Telegram identity.
Walk-in customers (no Telegram) cannot authenticate here — they are created
by barbers via the walk-in endpoint.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TelegramUser
from app.core.database import get_db
from app.models.customer import Customer


async def get_current_customer(
    user: TelegramUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Customer:
    """
    Resolve (or create on first visit) a Customer from the verified Telegram user.

    The Customer record is the platform-wide shared identity. Per-barber
    relationship data lives in BarberCustomer (created on booking).
    """
    telegram_id: int | None = user.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram foydalanuvchi ID olinmadi",
        )

    stmt = select(Customer).where(Customer.telegram_id == telegram_id)
    customer = (await db.execute(stmt)).scalars().first()

    if customer is None:
        # First visit — auto-create the customer identity from Telegram profile
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or "Telegram foydalanuvchi"
        customer = Customer(telegram_id=telegram_id, full_name=full_name)
        db.add(customer)
        await db.flush()

    return customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
