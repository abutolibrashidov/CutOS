"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router

# Barber routers
from app.api.v1.barber.profile import router as profile_router
from app.api.v1.barber.services import router as services_router
from app.api.v1.barber.schedule import router as schedule_router
from app.api.v1.barber.blocked_times import router as blocked_times_router
from app.api.v1.barber.appointments import router as barber_appointments_router

# Customer routers
from app.api.v1.customer.locations import router as locations_router
from app.api.v1.customer.barbers import router as customer_barbers_router
from app.api.v1.customer.services import router as customer_services_router
from app.api.v1.customer.availability import router as availability_router
from app.api.v1.customer.book import router as book_router
from app.api.v1.customer.appointments import router as customer_appointments_router

api_router = APIRouter(prefix="/api/v1")

# System
api_router.include_router(health_router)

# ── Barber routes ────────────────────────────────────────────────────────────
barber_router = APIRouter(prefix="/barber")
barber_router.include_router(profile_router)
barber_router.include_router(services_router, prefix="/services")
barber_router.include_router(schedule_router, prefix="/schedule")
barber_router.include_router(blocked_times_router, prefix="/blocked-times")
barber_router.include_router(barber_appointments_router, prefix="/appointments")

api_router.include_router(barber_router)

# ── Customer routes ──────────────────────────────────────────────────────────
customer_router = APIRouter(prefix="/customer")
customer_router.include_router(locations_router, prefix="/locations")
customer_router.include_router(customer_barbers_router, prefix="/barbers")
# Services are nested under /barbers/{barber_id}/services/
customer_router.include_router(customer_services_router, prefix="/barbers")
# Availability slots nested under /barbers/{barber_id}/available-slots/
customer_router.include_router(availability_router, prefix="/barbers")
customer_router.include_router(book_router, prefix="/book")
customer_router.include_router(customer_appointments_router, prefix="/appointments")

api_router.include_router(customer_router)
