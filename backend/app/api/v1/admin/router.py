"""Admin API router — handles administrative endpoints."""

from fastapi import APIRouter, Depends

from app.core.admin_auth import CurrentAdmin, get_current_admin

from app.api.v1.admin.barbers import router as barbers_router
from app.api.v1.admin.locations import router as locations_router

admin_router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
admin_router.include_router(barbers_router)
admin_router.include_router(locations_router)


@admin_router.get("/me")
async def check_admin_status(admin: CurrentAdmin) -> dict:
    """Verify that current user is an authorized admin."""
    return {"is_admin": True, "telegram_id": admin.get("id")}


