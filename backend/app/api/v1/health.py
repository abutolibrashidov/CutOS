"""Health check endpoint."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.get("/health", tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Health check endpoint.

    Verifies that the application is running and the database is reachable.
    Returns 200 if healthy and 503 if the database is unreachable.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ma'lumotlar bazasi vaqtincha ishlamayapti",
        ) from exc

    return {
        "status": "ok",
        "database": "ok",
    }
