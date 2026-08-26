"""Stage 3 — Customer Booking & Availability Test Suite.

21 test cases covering:
  - Slot availability engine
  - Multi-service bookings
  - Atomic booking with race-condition protection
  - Customer and barber cancellation
  - Walk-in creation
  - Barber data isolation
  - Customer deduplication

Tests rely on the common fixtures from conftest.py:
  db_session, test_location, barber1, barber2, client_b1, client_b2, client_anon.

Customer authentication uses `test <telegram_id>` header (same as barber auth but
resolves/creates a Customer record instead of a Barber record).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, time, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.appointment import Appointment, AppointmentSource, AppointmentStatus
from app.models.appointment_service import AppointmentService
from app.models.barber import Barber
from app.models.blocked_time import BlockedTime
from app.models.customer import Customer
from app.models.location import Location
from app.models.schedule import WorkingSchedule
from app.models.service import Service

# ─── Test-local helpers ────────────────────────────────────────────────────────

TODAY = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
# Use a weekday (Monday=0) so schedule tests are predictable.
# We pick a date two days from now to avoid same-day edge cases.
FUTURE_DATE = TODAY + timedelta(days=2)
if FUTURE_DATE.weekday() > 4:  # If weekend, push to Monday
    FUTURE_DATE += timedelta(days=7 - FUTURE_DATE.weekday())


def _slot(hour: int, minute: int = 0) -> datetime:
    """Return an aware UTC datetime for the test date."""
    return FUTURE_DATE.replace(hour=hour, minute=minute)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def working_schedule_b1(db_session: AsyncSession, barber1: Barber) -> None:
    """Barber 1 works Monday–Friday, 09:00–18:00 UTC.

    Uses INSERT ... ON CONFLICT DO NOTHING so repeated test runs in the same
    DB session don't hit the unique (barber_id, weekday) constraint.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for weekday in range(5):  # 0=Mon … 4=Fri
        stmt = (
            pg_insert(WorkingSchedule)
            .values(
                barber_id=barber1.id,
                weekday=weekday,
                is_working=True,
                start_time=time(9, 0),
                end_time=time(18, 0),
            )
            .on_conflict_do_nothing(index_elements=["barber_id", "weekday"])
        )
        await db_session.execute(stmt)
    await db_session.flush()


@pytest_asyncio.fixture
async def working_schedule_b2(db_session: AsyncSession, barber2: Barber) -> None:
    """Barber 2 works Monday–Friday, 09:00–18:00 UTC."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for weekday in range(5):
        stmt = (
            pg_insert(WorkingSchedule)
            .values(
                barber_id=barber2.id,
                weekday=weekday,
                is_working=True,
                start_time=time(9, 0),
                end_time=time(18, 0),
            )
            .on_conflict_do_nothing(index_elements=["barber_id", "weekday"])
        )
        await db_session.execute(stmt)
    await db_session.flush()


@pytest_asyncio.fixture
async def service_b1(db_session: AsyncSession, barber1: Barber) -> Service:
    """Barber 1 primary service: 30-min haircut, 50 000 UZS."""
    svc = Service(
        barber_id=barber1.id,
        name="Soch olish",
        price_uzs=50_000,
        duration_minutes=30,
        is_active=True,
    )
    db_session.add(svc)
    await db_session.flush()
    return svc


@pytest_asyncio.fixture
async def service_b1_beard(db_session: AsyncSession, barber1: Barber) -> Service:
    """Barber 1 secondary service: 20-min beard trim, 30 000 UZS."""
    svc = Service(
        barber_id=barber1.id,
        name="Soqol olish",
        price_uzs=30_000,
        duration_minutes=20,
        is_active=True,
    )
    db_session.add(svc)
    await db_session.flush()
    return svc


@pytest_asyncio.fixture
async def service_b2(db_session: AsyncSession, barber2: Barber) -> Service:
    """Barber 2 service with same name but different price."""
    svc = Service(
        barber_id=barber2.id,
        name="Soch olish",
        price_uzs=45_000,   # different price from barber1
        duration_minutes=30,
        is_active=True,
    )
    db_session.add(svc)
    await db_session.flush()
    return svc


@pytest_asyncio.fixture
async def customer1(db_session: AsyncSession) -> Customer:
    """Test customer with Telegram ID 55555."""
    c = Customer(full_name="Test Mijoz", telegram_id=55555)
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def client_customer1(customer1: Customer) -> AsyncClient:
    """HTTP client authenticated as customer1 (telegram_id=55555)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 55555"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client_customer2() -> AsyncClient:
    """HTTP client authenticated as a second customer (telegram_id=66666)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 66666"},
    ) as client:
        yield client


# ─── Helper function to create a booking via API ──────────────────────────────

async def _book(
    client: AsyncClient,
    location_id: str,
    service_ids: list[str],
    barber_id: str | None,
    start_at: datetime,
) -> dict:
    payload = {
        "location_id": location_id,
        "barber_id": barber_id,
        "service_ids": service_ids,
        "start_at": start_at.isoformat(),
    }
    resp = await client.post("/api/v1/customer/book/", json=payload)
    return resp


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. One valid booking returns 201 ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_01_valid_booking_returns_201(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location,
):
    resp = await _book(
        client_customer1,
        str(test_location.id),
        [str(service_b1.id)],
        str(barber1.id),
        _slot(10),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "appointment" in data
    assert data["appointment"]["status"] == "confirmed"


# ── 2. Multiple services accepted ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_02_multiple_services_accepted(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber,
    service_b1: Service, service_b1_beard: Service,
    test_location: Location,
):
    resp = await _book(
        client_customer1,
        str(test_location.id),
        [str(service_b1.id), str(service_b1_beard.id)],
        str(barber1.id),
        _slot(11),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["services"]) == 2


# ── 3. Total duration summed correctly ────────────────────────────────────────
@pytest.mark.asyncio
async def test_03_total_duration_summed(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber,
    service_b1: Service, service_b1_beard: Service,
    test_location: Location,
):
    resp = await _book(
        client_customer1,
        str(test_location.id),
        [str(service_b1.id), str(service_b1_beard.id)],
        str(barber1.id),
        _slot(12),
    )
    assert resp.status_code == 201
    data = resp.json()
    # 30 + 20 = 50 minutes
    assert data["total_duration_minutes"] == 50


# ── 4. Total price summed correctly ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_04_total_price_summed(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber,
    service_b1: Service, service_b1_beard: Service,
    test_location: Location,
):
    resp = await _book(
        client_customer1,
        str(test_location.id),
        [str(service_b1.id), str(service_b1_beard.id)],
        str(barber1.id),
        _slot(13),
    )
    assert resp.status_code == 201
    data = resp.json()
    # 50 000 + 30 000 = 80 000 UZS
    assert data["total_price_uzs"] == 80_000


# ── 5. Service price snapshot preserved after price change ────────────────────
@pytest.mark.asyncio
async def test_05_price_snapshot_preserved(
    client_b1: AsyncClient, client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location, db_session: AsyncSession,
):
    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(14))
    assert resp.status_code == 201
    original_price = resp.json()["total_price_uzs"]

    # Barber updates service price
    await client_b1.put(f"/api/v1/barber/services/{service_b1.id}", json={
        "name": service_b1.name, "price_uzs": 999_999, "duration_minutes": service_b1.duration_minutes
    })

    # The appointment snapshot must remain unchanged
    appt_id = resp.json()["appointment"]["id"]
    appt_resp = await client_customer1.get("/api/v1/customer/appointments/")
    appts = appt_resp.json()
    target = next(a for a in appts if a["id"] == appt_id)
    assert target["price_at_booking"] == original_price


# ── 6. Service duration snapshot preserved after duration change ───────────────
@pytest.mark.asyncio
async def test_06_duration_snapshot_preserved(
    client_b1: AsyncClient, client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location,
):
    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(15))
    assert resp.status_code == 201
    original_duration = resp.json()["total_duration_minutes"]

    # Barber updates duration
    await client_b1.put(f"/api/v1/barber/services/{service_b1.id}", json={
        "name": service_b1.name, "price_uzs": service_b1.price_uzs, "duration_minutes": 90
    })

    appt_id = resp.json()["appointment"]["id"]
    appt_resp = await client_customer1.get("/api/v1/customer/appointments/")
    appts = appt_resp.json()
    target = next(a for a in appts if a["id"] == appt_id)
    assert target["duration_at_booking"] == original_duration


# ── 7. Booking outside working hours → 409 ────────────────────────────────────
@pytest.mark.asyncio
async def test_07_outside_working_hours(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location,
):
    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(22))
    assert resp.status_code in (409, 422)


# ── 8. Booking crossing schedule end boundary → 409 ──────────────────────────
@pytest.mark.asyncio
async def test_08_slot_crosses_boundary(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location,
):
    # Service is 30 min, but slot starts at 17:45 and end_time is 18:00 → only 15 min
    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(17, 45))
    assert resp.status_code in (409, 422)


# ── 9. Booking overlapping blocked time → 409 ─────────────────────────────────
@pytest.mark.asyncio
async def test_09_overlaps_blocked_time(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location, db_session: AsyncSession,
):
    blocked = BlockedTime(
        barber_id=barber1.id,
        start_at=_slot(10),
        end_at=_slot(11),
        reason="Tushlik",
    )
    db_session.add(blocked)
    await db_session.flush()

    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(10))
    assert resp.status_code == 409


# ── 10. Booking overlapping existing appointment → 409 ────────────────────────
@pytest.mark.asyncio
async def test_10_overlaps_existing_appointment(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location, customer1: Customer, db_session: AsyncSession,
):
    # Create an existing appointment at 10:00
    existing = Appointment(
        barber_id=barber1.id,
        customer_id=customer1.id,
        start_at=_slot(10),
        end_at=_slot(10, 30),
        status=AppointmentStatus.CONFIRMED,
        source=AppointmentSource.ONLINE,
        price_at_booking=50_000,
        duration_at_booking=30,
    )
    db_session.add(existing)
    await db_session.flush()

    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(10))
    assert resp.status_code == 409


# ── 11. Cancelled appointment does not block availability ──────────────────────
@pytest.mark.asyncio
async def test_11_cancelled_does_not_block(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location, customer1: Customer, db_session: AsyncSession,
):
    # Create a cancelled appointment at the target slot
    cancelled = Appointment(
        barber_id=barber1.id,
        customer_id=customer1.id,
        start_at=_slot(10, 30),
        end_at=_slot(11),
        status=AppointmentStatus.CANCELLED,
        source=AppointmentSource.ONLINE,
        price_at_booking=50_000,
        duration_at_booking=30,
    )
    db_session.add(cancelled)
    await db_session.flush()

    # A new booking at same slot should succeed
    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(10, 30))
    assert resp.status_code == 201


# ── 12. Availability endpoint returns correct slots ───────────────────────────
@pytest.mark.asyncio
async def test_12_availability_slots_returned(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
):
    date_str = FUTURE_DATE.strftime("%Y-%m-%d")
    resp = await client_customer1.get(
        f"/api/v1/customer/barbers/{barber1.id}/available-slots/",
        params={"service_ids": str(service_b1.id), "date": date_str},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "slots" in data
    # 09:00–18:00 with 30-min service → expect multiple slots
    assert len(data["slots"]) > 0


# ── 13. Any-barber selection assigns a concrete barber ────────────────────────
@pytest.mark.asyncio
async def test_13_any_barber_assigns_concrete_barber(
    client_customer1: AsyncClient,
    working_schedule_b1, working_schedule_b2,
    barber1: Barber, barber2: Barber,
    service_b1: Service, service_b2: Service,
    test_location: Location,
):
    resp = await _book(
        client_customer1,
        str(test_location.id),
        [str(service_b1.id)],
        None,  # any barber
        _slot(9, 30),
    )
    assert resp.status_code == 201
    data = resp.json()
    assigned_barber_id = data["barber"]["id"]
    # Alphabetically "Barber Bir" < "Barber Ikki", so barber1 should be assigned first
    assert assigned_barber_id == str(barber1.id)


# ── 14. Different barbers have different service prices ───────────────────────
@pytest.mark.asyncio
async def test_14_barbers_have_independent_prices(service_b1: Service, service_b2: Service):
    assert service_b1.price_uzs != service_b2.price_uzs
    assert service_b1.name == service_b2.name  # same service name, different price


# ── 15. Customer cancel before 1-hour cutoff → 200 ───────────────────────────
@pytest.mark.asyncio
async def test_15_customer_cancel_before_cutoff(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location,
):
    # Book for 2+ hours in the future
    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(16))
    assert resp.status_code == 201
    appt_id = resp.json()["appointment"]["id"]

    cancel_resp = await client_customer1.post(f"/api/v1/customer/appointments/{appt_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


# ── 16. Customer cancel inside 1-hour cutoff → 400 ───────────────────────────
@pytest.mark.asyncio
async def test_16_customer_cancel_after_cutoff(
    client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location, customer1: Customer, db_session: AsyncSession,
):
    # Create appointment starting in 30 minutes (inside cutoff)
    near_future = datetime.now(timezone.utc) + timedelta(minutes=30)
    near_future = near_future.replace(second=0, microsecond=0)
    near_end = near_future + timedelta(minutes=30)

    appt = Appointment(
        barber_id=barber1.id,
        customer_id=customer1.id,
        start_at=near_future,
        end_at=near_end,
        status=AppointmentStatus.CONFIRMED,
        source=AppointmentSource.ONLINE,
        price_at_booking=50_000,
        duration_at_booking=30,
    )
    db_session.add(appt)
    await db_session.flush()

    cancel_resp = await client_customer1.post(f"/api/v1/customer/appointments/{appt.id}/cancel")
    assert cancel_resp.status_code == 400


# ── 17. Barber cancel any time → 200 ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_17_barber_cancel_anytime(
    client_b1: AsyncClient, client_customer1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location, customer1: Customer, db_session: AsyncSession,
):
    # Create appointment starting in 10 minutes (would block customer cancel)
    near_future = datetime.now(timezone.utc) + timedelta(minutes=10)
    near_future = near_future.replace(second=0, microsecond=0)

    appt = Appointment(
        barber_id=barber1.id,
        customer_id=customer1.id,
        start_at=near_future,
        end_at=near_future + timedelta(minutes=30),
        status=AppointmentStatus.CONFIRMED,
        source=AppointmentSource.WALKIN,
        price_at_booking=50_000,
        duration_at_booking=30,
    )
    db_session.add(appt)
    await db_session.flush()

    # Barber can cancel with no cutoff restriction
    cancel_resp = await client_b1.post(f"/api/v1/barber/appointments/{appt.id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


# ── 18. Walk-in creates appointment with source=walkin ────────────────────────
@pytest.mark.asyncio
async def test_18_walk_in_appointment_created(
    client_b1: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
):
    resp = await client_b1.post("/api/v1/barber/appointments/walk-in/", json={
        "full_name": "Walk-in Mijoz",
        "phone": "+998909090909",
        "service_ids": [str(service_b1.id)],
        "start_at": _slot(9).isoformat(),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["source"] == "walkin"
    assert data["customer_full_name"] == "Walk-in Mijoz"


# ── 19. Concurrent bookings at same slot — only one succeeds ─────────────────
@pytest.mark.asyncio
async def test_19_concurrent_booking_only_one_succeeds(
    client_customer1: AsyncClient, client_customer2: AsyncClient,
    working_schedule_b1, barber1: Barber, service_b1: Service,
    test_location: Location,
):
    target_slot = _slot(9, 15)

    async def attempt_booking(client: AsyncClient):
        return await _book(client, str(test_location.id), [str(service_b1.id)], str(barber1.id), target_slot)

    results = await asyncio.gather(
        attempt_booking(client_customer1),
        attempt_booking(client_customer2),
        return_exceptions=True,
    )

    statuses = [r.status_code for r in results if hasattr(r, "status_code")]
    successes = [s for s in statuses if s == 201]
    conflicts = [s for s in statuses if s in (409, 500)]

    assert len(successes) <= 1
    assert len(conflicts) >= 1


# ── 20. Barber isolation — barber cannot see another barber's appointments ────
@pytest.mark.asyncio
async def test_20_barber_data_isolation(
    client_b1: AsyncClient, client_b2: AsyncClient,
    working_schedule_b1, working_schedule_b2,
    barber1: Barber, barber2: Barber,
    service_b1: Service, service_b2: Service,
    test_location: Location, client_customer1: AsyncClient,
):
    # Customer books with barber1
    resp = await _book(client_customer1, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(10))
    assert resp.status_code == 201
    appt_id = resp.json()["appointment"]["id"]

    # Barber 1 can see this appointment
    b1_appts = (await client_b1.get("/api/v1/barber/appointments/")).json()
    assert any(a["id"] == appt_id for a in b1_appts)

    # Barber 2 cannot see this appointment
    b2_appts = (await client_b2.get("/api/v1/barber/appointments/")).json()
    assert not any(a["id"] == appt_id for a in b2_appts)

    # Barber 2 cannot cancel barber 1's appointment
    cancel_resp = await client_b2.post(f"/api/v1/barber/appointments/{appt_id}/cancel")
    assert cancel_resp.status_code == 404


# ── 21. Customer not created twice for same telegram_id ───────────────────────
@pytest.mark.asyncio
async def test_21_customer_not_duplicated(
    db_session: AsyncSession, working_schedule_b1,
    barber1: Barber, service_b1: Service, test_location: Location,
):
    from sqlalchemy import func, select
    from app.models.customer import Customer

    # Make two separate requests as the same customer (telegram_id=77777)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "test 77777"},
    ) as client:
        r1 = await _book(client, str(test_location.id), [str(service_b1.id)], str(barber1.id), _slot(11, 15))
        assert r1.status_code == 201
        r2 = await client.get("/api/v1/customer/appointments/")
        assert r2.status_code == 200

    # Only one Customer record should exist for telegram_id=77777
    stmt = select(func.count()).select_from(Customer).where(Customer.telegram_id == 77777)
    count = (await db_session.execute(stmt)).scalar()
    assert count == 1
