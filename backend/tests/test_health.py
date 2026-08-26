"""Tests for the FastAPI application health and basic startup."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_barber
from app.core.database import get_db
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_responds() -> None:
    """Health endpoint should return 200 OK."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint_includes_database_field() -> None:
    """Health endpoint should always include a 'database' field."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")

    data = response.json()
    assert "database" in data


def test_models_importable() -> None:
    """All core models must be importable without errors."""
    from app.models import (  # noqa: F401
        Appointment,
        AppointmentSource,
        AppointmentStatus,
        Barber,
        BarberCustomer,
        BlockedTime,
        Customer,
        Expense,
        Location,
        Service,
        UUIDBase,
        WorkingSchedule,
    )


def test_app_title() -> None:
    """FastAPI app should have the correct title."""
    assert "Barber" in app.title or "CutOS" in app.title


@pytest.mark.asyncio
async def test_health_endpoint_returns_503_when_database_is_unavailable() -> None:
    class FailingSession:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("database unavailable")

    async def failing_db():
        yield FailingSession()

    app.dependency_overrides[get_db] = failing_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Ma'lumotlar bazasi vaqtincha ishlamayapti"


@pytest.mark.asyncio
async def test_validation_errors_are_returned_in_uzbek() -> None:
    async def fake_current_barber():
        return None

    app.dependency_overrides[get_current_barber] = fake_current_barber
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/barber/services/not-a-uuid")
    finally:
        app.dependency_overrides.pop(get_current_barber, None)

    assert response.status_code == 422
    assert response.json()["detail"] == "Kiritilgan ma'lumotlar noto'g'ri"
