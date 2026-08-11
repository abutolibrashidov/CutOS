import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.barber import Barber
from app.models.service import Service
from app.models.schedule import WorkingSchedule
from app.models.blocked_time import BlockedTime
from app.models.appointment import Appointment, AppointmentStatus, AppointmentSource


@pytest.mark.asyncio
async def test_barber_profile_endpoints(
    client_b1: AsyncClient,
    client_b2: AsyncClient,
    barber1: Barber,
    barber2: Barber,
) -> None:
    # 1. Fetch own profile
    res1 = await client_b1.get("/api/v1/barber/profile")
    assert res1.status_code == 200
    data = res1.json()
    assert data["full_name"] == barber1.full_name
    assert data["telegram_id"] == barber1.telegram_id

    # Make sure we cannot modify other's profile because there's no endpoint
    # taking arbitrary barber_id (endpoints are bound to current_barber).

    # 2. Update own profile
    update_payload = {
        "full_name": "Yangi Ism",
        "phone": "+998909999999",
        "bio": "Usta sartarosh",
        "avatar_url": "http://photo.com",
    }
    res_up = await client_b1.put("/api/v1/barber/profile", json=update_payload)
    assert res_up.status_code == 200
    updated_data = res_up.json()
    assert updated_data["full_name"] == "Yangi Ism"
    assert updated_data["phone"] == "+998909999999"


@pytest.mark.asyncio
async def test_services_crud_and_isolation(
    client_b1: AsyncClient,
    client_b2: AsyncClient,
    barber1: Barber,
    barber2: Barber,
    db_session: AsyncSession,
) -> None:
    # 1. Create a service for Barber 1
    create_payload = {
        "name": "Classic Haircut",
        "price_uzs": 80000,
        "duration_minutes": 45,
    }
    res_create = await client_b1.post("/api/v1/barber/services/", json=create_payload)
    assert res_create.status_code == 201
    service1 = res_create.json()
    assert service1["name"] == "Classic Haircut"
    assert service1["price_uzs"] == 80000
    assert service1["duration_minutes"] == 45

    # 2. List own services (Barber 1 should see it, Barber 2 should not)
    list1 = await client_b1.get("/api/v1/barber/services/")
    assert any(s["id"] == service1["id"] for s in list1.json())

    list2 = await client_b2.get("/api/v1/barber/services/")
    assert not any(s["id"] == service1["id"] for s in list2.json())

    # 3. Barber 2 tries to GET Barber 1's service details -> 404/403
    res_get_unauthorized = await client_b2.get(f"/api/v1/barber/services/{service1['id']}")
    assert res_get_unauthorized.status_code == 404

    # 4. Service validation: price < 0 should fail
    fail_payload = {"name": "Test Fail", "price_uzs": -100, "duration_minutes": 30}
    res_fail = await client_b1.post("/api/v1/barber/services/", json=fail_payload)
    assert res_fail.status_code == 422

    # 5. Service validation: duration <= 0 should fail
    fail_payload2 = {"name": "Test Fail 2", "price_uzs": 50000, "duration_minutes": 0}
    res_fail2 = await client_b1.post("/api/v1/barber/services/", json=fail_payload2)
    assert res_fail2.status_code == 422

    # 6. Update service configs
    update_payload = {"price_uzs": 90000, "duration_minutes": 50, "is_active": False}
    res_update = await client_b1.put(f"/api/v1/barber/services/{service1['id']}", json=update_payload)
    assert res_update.status_code == 200
    assert res_update.json()["price_uzs"] == 90000
    assert res_update.json()["is_active"] is False

    # Barber 2 tries to update Barber 1's service -> 404
    res_update_unauthorized = await client_b2.put(
        f"/api/v1/barber/services/{service1['id']}",
        json={"price_uzs": 100000},
    )
    assert res_update_unauthorized.status_code == 404

    # 7. Delete Service check:
    # Service without appointments can be hard deleted
    res_delete = await client_b1.delete(f"/api/v1/barber/services/{service1['id']}")
    assert res_delete.status_code == 204

    # Verify deleted from DB
    res_verify = await client_b1.get(f"/api/v1/barber/services/{service1['id']}")
    assert res_verify.status_code == 404

    # Create another service and link it to an appointment
    create_payload2 = {
        "name": "Low Fade",
        "price_uzs": 120000,
        "duration_minutes": 35,
    }
    res_create2 = await client_b1.post("/api/v1/barber/services/", json=create_payload2)
    service2_id = res_create2.json()["id"]

    # We need a Customer in DB to create Appointment
    from app.models.customer import Customer
    c = Customer(full_name="Mijoz Shahboz")
    db_session.add(c)
    await db_session.flush()

    # Link an appointment to this service
    import datetime
    start = datetime.datetime.now(datetime.timezone.utc)
    end = start + datetime.timedelta(minutes=35)
    appt = Appointment(
        barber_id=barber1.id,
        customer_id=c.id,
        service_id=service2_id,
        start_at=start,
        end_at=end,
        status="confirmed",
        source="online",
        service_name_at_booking="Low Fade",
        price_at_booking=120000,
        duration_at_booking=35
    )
    db_session.add(appt)
    await db_session.flush()

    # Now deletion should fail and tell us to deactivate
    res_delete_failed = await client_b1.delete(f"/api/v1/barber/services/{service2_id}")
    assert res_delete_failed.status_code == 400
    assert "o'chirib bo'lmaydi" in res_delete_failed.json()["detail"]


@pytest.mark.asyncio
async def test_working_schedule(
    client_b1: AsyncClient,
    client_b2: AsyncClient,
    barber1: Barber,
    barber2: Barber,
) -> None:
    # 1. Update weekly schedule for Monday (0) and Tuesday (1)
    # format: weekday, start_time, end_time, is_working
    update_payload = [
        {"weekday": 0, "start_time": "09:00:00", "end_time": "18:00:00", "is_working": True},
        {"weekday": 1, "start_time": "10:00:00", "end_time": "17:00:00", "is_working": False},
    ]

    res_post = await client_b1.post("/api/v1/barber/schedule/", json=update_payload)
    assert res_post.status_code == 200
    data = res_post.json()
    assert len(data) == 2
    assert data[0]["weekday"] == 0
    assert data[0]["is_working"] is True
    assert data[1]["weekday"] == 1
    assert data[1]["is_working"] is False

    # 2. Get schedule
    res_get = await client_b1.get("/api/v1/barber/schedule/")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert len(get_data) >= 2

    # Every barber receives a complete seven-day grid, including OFF days.
    res_get2 = await client_b2.get("/api/v1/barber/schedule/")
    schedule2 = res_get2.json()
    assert len(schedule2) == 7
    assert all(day["is_working"] is False for day in schedule2)
    assert all(day["start_time"] is None and day["end_time"] is None for day in schedule2)

    invalid_schedule = [{"weekday": 2, "start_time": "18:00:00", "end_time": "09:00:00"}]
    invalid_schedule_response = await client_b1.post(
        "/api/v1/barber/schedule/", json=invalid_schedule
    )
    assert invalid_schedule_response.status_code == 422


@pytest.mark.asyncio
async def test_blocked_times(
    client_b1: AsyncClient,
    client_b2: AsyncClient,
    barber1: Barber,
    barber2: Barber,
) -> None:
    import datetime

    # UTC timestamps
    start = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    end = start + datetime.timedelta(hours=1)

    payload = {
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
        "reason": "Lunch break",
    }

    # 1. Create blocked time
    res_create = await client_b1.post("/api/v1/barber/blocked-times/", json=payload)
    assert res_create.status_code == 201
    blocked = res_create.json()
    assert blocked["reason"] == "Lunch break"

    invalid_range = await client_b1.post(
        "/api/v1/barber/blocked-times/",
        json={"start_at": end.isoformat(), "end_at": start.isoformat()},
    )
    assert invalid_range.status_code == 422

    naive_time = await client_b1.post(
        "/api/v1/barber/blocked-times/",
        json={"start_at": "2026-08-12T09:00:00", "end_at": "2026-08-12T10:00:00"},
    )
    assert naive_time.status_code == 422

    # Update own blocked period.
    updated_end = end + datetime.timedelta(minutes=30)
    update_payload = {
        "start_at": start.isoformat(),
        "end_at": updated_end.isoformat(),
        "reason": "Shaxsiy ish",
    }
    res_update = await client_b1.put(
        f"/api/v1/barber/blocked-times/{blocked['id']}", json=update_payload
    )
    assert res_update.status_code == 200
    assert res_update.json()["reason"] == "Shaxsiy ish"

    # 2. List blocked times
    res_list1 = await client_b1.get("/api/v1/barber/blocked-times/")
    assert any(b["id"] == blocked["id"] for b in res_list1.json())

    # Barber 2 list should not contain it
    res_list2 = await client_b2.get("/api/v1/barber/blocked-times/")
    assert not any(b["id"] == blocked["id"] for b in res_list2.json())

    # Barber 2 tries to delete Barber 1's blocked time -> 404
    res_del_fail = await client_b2.delete(f"/api/v1/barber/blocked-times/{blocked['id']}")
    assert res_del_fail.status_code == 404

    res_update_fail = await client_b2.put(
        f"/api/v1/barber/blocked-times/{blocked['id']}", json=update_payload
    )
    assert res_update_fail.status_code == 404

    # Barber 1 deletes own blocked time
    res_del_ok = await client_b1.delete(f"/api/v1/barber/blocked-times/{blocked['id']}")
    assert res_del_ok.status_code == 204
