"""
Admin authorization dependency.

Validates that the authenticated Telegram user is present in the configured
ADMIN_TELEGRAM_IDS allowlist.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.auth import TelegramUser
from app.core.config import get_settings

settings = get_settings()


async def get_current_admin(user: TelegramUser) -> dict:
    """
    FastAPI dependency: ensure verified Telegram user is an authorized admin.

    Raises HTTP 403 Forbidden if user's Telegram ID is not in ADMIN_TELEGRAM_IDS.
    """
    telegram_id = user.get("id")
    if not telegram_id or telegram_id not in settings.admin_telegram_ids_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ruxsat berilmadi. Administrator huquqi yo'q.",
        )

    return user


CurrentAdmin = Annotated[dict, Depends(get_current_admin)]
