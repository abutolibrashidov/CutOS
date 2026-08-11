import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

from app.core import auth


FAKE_BOT_TOKEN = "test-bot-token-not-a-real-secret"


def make_init_data(fields: dict[str, str]) -> str:
    """Build realistically URL-encoded Telegram Mini App initData for tests."""
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", FAKE_BOT_TOKEN.encode(), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": data_hash})


def valid_fields(*, auth_date: str | None = None) -> dict[str, str]:
    user = {"id": 123456, "first_name": "Ali & Vali", "username": "ali=barber"}
    return {
        "auth_date": auth_date or str(int(datetime.now(timezone.utc).timestamp())),
        "query_id": "AAEAAQ",
        "user": json.dumps(user, separators=(",", ":")),
    }


@pytest.fixture(autouse=True)
def fake_telegram_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.settings, "TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setattr(auth.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(auth.settings, "TELEGRAM_INIT_DATA_MAX_AGE_SECONDS", 3600)
    monkeypatch.setattr(auth.settings, "TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS", 30)


def test_valid_init_data_and_encoded_values_are_accepted() -> None:
    data = auth.verify_telegram_init_data(make_init_data(valid_fields()))
    assert json.loads(data["user"])["first_name"] == "Ali & Vali"
    assert data["query_id"] == "AAEAAQ"


def test_invalid_hash_is_rejected() -> None:
    init_data = make_init_data(valid_fields())
    with pytest.raises(ValueError, match="signature"):
        auth.verify_telegram_init_data(init_data.rsplit("hash=", 1)[0] + "hash=" + "0" * 64)


def test_modified_user_data_is_rejected() -> None:
    init_data = make_init_data(valid_fields()).replace("Ali", "Vali")
    with pytest.raises(ValueError, match="signature"):
        auth.verify_telegram_init_data(init_data)


@pytest.mark.parametrize(
    "auth_date",
    ["", "not-a-timestamp"],
)
def test_missing_or_malformed_auth_date_is_rejected(auth_date: str) -> None:
    fields = valid_fields()
    if auth_date:
        fields["auth_date"] = auth_date
    else:
        del fields["auth_date"]
    with pytest.raises(ValueError, match="auth_date"):
        auth.verify_telegram_init_data(make_init_data(fields))


def test_expired_auth_date_is_rejected() -> None:
    expired = str(int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()))
    with pytest.raises(ValueError, match="amal qilish"):
        auth.verify_telegram_init_data(make_init_data(valid_fields(auth_date=expired)))


def test_future_auth_date_beyond_clock_skew_is_rejected() -> None:
    future = str(int((datetime.now(timezone.utc) + timedelta(minutes=2)).timestamp()))
    with pytest.raises(ValueError, match="vaqti noto'g'ri"):
        auth.verify_telegram_init_data(make_init_data(valid_fields(auth_date=future)))


@pytest.mark.asyncio
async def test_missing_user_is_rejected_by_auth_dependency() -> None:
    fields = {"auth_date": str(int(datetime.now(timezone.utc).timestamp()))}
    with pytest.raises(HTTPException, match="foydalanuvchi"):
        await auth.get_telegram_user(authorization=f"tma {make_init_data(fields)}")


@pytest.mark.asyncio
async def test_development_authentication_is_allowed() -> None:
    user = await auth.get_telegram_user(authorization="test 123456")
    assert user["id"] == 123456
    assert user["is_test"] is True


@pytest.mark.asyncio
async def test_production_rejects_development_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.settings, "ENVIRONMENT", "production")
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_telegram_user(authorization="test 123456")
    assert exc_info.value.status_code == 401
