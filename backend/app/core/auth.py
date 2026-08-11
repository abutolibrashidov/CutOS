"""
Telegram Mini App authentication via initData HMAC verification.

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

The Telegram Web App passes an `initData` string (URL-encoded) to the frontend.
The frontend sends it in the Authorization header as:
    Authorization: tma <initData>

The backend verifies the HMAC-SHA256 signature using the bot token.
This is the ONLY trusted authentication mechanism — never trust arbitrary
telegram_id values sent directly by the client.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.barber import Barber

logger = logging.getLogger(__name__)

settings = get_settings()


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Validate the Telegram Mini App initData string.

    Returns the parsed data dict if valid.
    Raises ValueError if invalid or expired.

    Algorithm:
    1. Parse the URL-encoded initData.
    2. Extract and remove the 'hash' field.
    3. Sort remaining fields alphabetically.
    4. Construct the data-check string: key=value\\nkey=value...
    5. Compute HMAC-SHA256 using a secret derived from the bot token.
    6. Compare with the extracted hash.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("initData noto'g'ri formatda") from exc

    # Telegram sends a URL-encoded query string. parse_qsl decodes each key and
    # value exactly once; decoding the whole string first can turn encoded data
    # such as %26 inside a name into a query-string separator.
    data: dict[str, str] = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("initData takroriy maydonlarga ega")
        data[key] = value

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash in initData")

    # Build the data_check_string
    sorted_items = sorted(data.items(), key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

    # Derive the secret key: HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.TELEGRAM_BOT_TOKEN.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # Compute expected hash
    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid initData signature")

    auth_date = data.get("auth_date")
    if auth_date is None:
        raise ValueError("auth_date mavjud emas")
    if not auth_date.isdecimal():
        raise ValueError("auth_date noto'g'ri")

    try:
        authenticated_at = datetime.fromtimestamp(int(auth_date), tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("auth_date noto'g'ri") from exc

    now = datetime.now(timezone.utc)
    age_seconds = (now - authenticated_at).total_seconds()
    if age_seconds > settings.TELEGRAM_INIT_DATA_MAX_AGE_SECONDS:
        raise ValueError("Telegram ma'lumotlarining amal qilish muddati tugagan")
    if age_seconds < -settings.TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS:
        raise ValueError("Telegram ma'lumotlarining vaqti noto'g'ri")

    return data


async def get_telegram_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """
    FastAPI dependency: extract and verify Telegram identity from initData.

    Expects header:  Authorization: tma <url-encoded-initData>
    OR (in development mode only): Authorization: test <telegram_id>

    Returns the parsed 'user' object from initData.
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentifikatsiya sarlavhasi mavjud emas",
        )

    # ── Dev Auth mode ────────────────────────────────────────────────────────
    if authorization.startswith("test "):
        if settings.ENVIRONMENT != "development":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sinov autentifikatsiyasiga faqat ishlab chiqish muhitida ruxsat beriladi",
            )
        try:
            telegram_id_str = authorization.removeprefix("test ").strip()
            telegram_id = int(telegram_id_str)
            return {"id": telegram_id, "first_name": "Test Barber", "is_test": True}
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sinov Telegram ID raqam bo'lishi kerak",
            ) from exc

    if not authorization.startswith("tma "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentifikatsiya sarlavhasi formati noto'g'ri",
        )

    init_data = authorization.removeprefix("tma ").strip()

    try:
        data = verify_telegram_init_data(init_data)
    except ValueError as exc:
        logger.warning("Telegram initData verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram autentifikatsiya ma'lumotlari noto'g'ri",
        ) from exc

    # Parse the nested user JSON
    import json  # noqa: PLC0415

    user_str = data.get("user")
    if not user_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram foydalanuvchi ma'lumotlari mavjud emas",
        )

    try:
        user = json.loads(user_str)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram foydalanuvchi ma'lumotlari noto'g'ri formatda",
        ) from exc

    return user


# Type alias for cleaner route signatures
TelegramUser = Annotated[dict, Depends(get_telegram_user)]


async def get_current_barber(
    user: TelegramUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Barber:
    """
    Get the authenticated barber from the database.

    Raises HTTP 403 Forbidden if the authenticated Telegram user is not
    registered as a Barber.
    """
    from sqlalchemy import select  # noqa: PLC0415
    from app.models.barber import Barber  # noqa: PLC0415

    telegram_id = user.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram foydalanuvchi ID olinmadi",
        )

    stmt = select(Barber).where(Barber.telegram_id == telegram_id, Barber.is_active == True)
    result = await db.execute(stmt)
    barber = result.scalars().first()

    if not barber:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ruxsat berilmadi. Barber tizimda ro'yxatdan o'tmagan yoki faol emas.",
        )

    return barber


CurrentBarber = Annotated[Barber, Depends(get_current_barber)]
