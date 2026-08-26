"""GET /api/v1/customer/locations/ — list active locations."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.location import Location
from app.schemas.customer import LocationPublic

router = APIRouter(tags=["customer-locations"])


@router.get("/", response_model=list[LocationPublic])
async def list_locations(db: AsyncSession = Depends(get_db)) -> list[LocationPublic]:
    """Return all active locations. No authentication required."""
    stmt = select(Location).where(Location.is_active == True).order_by(Location.name)  # noqa: E712
    rows = (await db.execute(stmt)).scalars().all()
    return [LocationPublic.model_validate(r) for r in rows]
