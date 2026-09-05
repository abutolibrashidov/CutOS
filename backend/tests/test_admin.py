import pytest
from httpx import ASGITransport, AsyncClient

from app.core import admin_auth
from app.main import app


@pytest.fixture(autouse=True)
def configure_admin_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set test admin Telegram ID allowlist."""
    monkeypatch.setattr(admin_auth.settings, "ADMIN_TELEGRAM_IDS", "99999,88888")
    monkeypatch.setattr(admin_auth.settings, "ENVIRONMENT", "development")


@pytest.mark.asyncio
async def test_admin_me_authorized() -> None:
    """Allowed admin Telegram ID receives 200 OK from /admin/me."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 99999"},
    ) as client:
        response = await client.get("/api/v1/admin/me")
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True
        assert data["telegram_id"] == 99999


@pytest.mark.asyncio
async def test_admin_me_forbidden_for_non_admin() -> None:
    """Non-admin Telegram ID receives 403 Forbidden from /admin/me."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 123456"},
    ) as client:
        response = await client.get("/api/v1/admin/me")
        assert response.status_code == 403
        assert "Administrator huquqi yo'q" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_me_unauthenticated() -> None:
    """Missing authentication header receives 401 Unauthorized."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/admin/me")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_create_and_provision_barber_flow(db_session, test_location) -> None:
    """
    Test full admin barber provisioning lifecycle:
    1. Admin creates barber record with numeric Telegram ID 77777.
    2. Newly created barber authenticates via existing get_current_barber dependency.
    3. Admin deactivates barber.
    4. Deactivated barber can no longer access barber endpoints (403 Forbidden).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 99999"},
    ) as admin_client:
        # 1. Admin creates barber
        payload = {
            "telegram_id": 77777,
            "full_name": "New Provisioned Barber",
            "phone": "+998907777777",
            "location_id": str(test_location.id),
            "bio": "Expert barber",
            "is_active": True,
        }
        create_res = await admin_client.post("/api/v1/admin/barbers/", json=payload)
        assert create_res.status_code == 201
        barber_data = create_res.json()
        assert barber_data["telegram_id"] == 77777
        assert barber_data["full_name"] == "New Provisioned Barber"
        assert barber_data["location_name"] == test_location.name
        barber_id = barber_data["id"]

        # 2. Duplicate telegram_id creation is rejected
        dup_res = await admin_client.post("/api/v1/admin/barbers/", json=payload)
        assert dup_res.status_code == 400
        assert "allaqachon barber" in dup_res.json()["detail"]

        # 3. List barbers
        list_res = await admin_client.get("/api/v1/admin/barbers/")
        assert list_res.status_code == 200
        assert any(b["id"] == barber_id for b in list_res.json())

    # 4. Provisioned barber logs into existing barber panel
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 77777"},
    ) as barber_client:
        profile_res = await barber_client.get("/api/v1/barber/profile")
        assert profile_res.status_code == 200
        profile = profile_res.json()
        assert profile["full_name"] == "New Provisioned Barber"
        assert profile["telegram_id"] == 77777

    # 5. Admin deactivates barber
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 99999"},
    ) as admin_client:
        status_res = await admin_client.patch(
            f"/api/v1/admin/barbers/{barber_id}/status",
            json={"is_active": False},
        )
        assert status_res.status_code == 200
        assert status_res.json()["is_active"] is False

    # 6. Deactivated barber gets 403 Forbidden
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 77777"},
    ) as barber_client:
        profile_res = await barber_client.get("/api/v1/barber/profile")
        assert profile_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_location_crud_flow(db_session) -> None:
    """Test admin creation and modification of physical shop locations."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 99999"},
    ) as admin_client:
        # 1. Create Location
        payload = {
            "name": "Chorsu Branch",
            "address": "Navoi St 10",
            "city": "Tashkent",
            "is_active": True,
        }
        create_res = await admin_client.post("/api/v1/admin/locations/", json=payload)
        assert create_res.status_code == 201
        loc_data = create_res.json()
        assert loc_data["name"] == "Chorsu Branch"
        loc_id = loc_data["id"]

        # 2. List Locations
        list_res = await admin_client.get("/api/v1/admin/locations/")
        assert list_res.status_code == 200
        assert any(l["id"] == loc_id for l in list_res.json())

        # 3. Update Location
        update_res = await admin_client.put(
            f"/api/v1/admin/locations/{loc_id}",
            json={"name": "Chorsu Flagship Branch", "city": "Tashkent City"},
        )
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Chorsu Flagship Branch"


