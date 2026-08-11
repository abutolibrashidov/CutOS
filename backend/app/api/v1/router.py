"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.barber.profile import router as profile_router
from app.api.v1.barber.services import router as services_router
from app.api.v1.barber.schedule import router as schedule_router
from app.api.v1.barber.blocked_times import router as blocked_times_router

api_router = APIRouter(prefix="/api/v1")

# System
api_router.include_router(health_router)

# Barber routes
barber_router = APIRouter(prefix="/barber")
barber_router.include_router(profile_router)
barber_router.include_router(services_router, prefix="/services")
barber_router.include_router(schedule_router, prefix="/schedule")
barber_router.include_router(blocked_times_router, prefix="/blocked-times")

api_router.include_router(barber_router)

# Customer routes (future stages)
# api_router.include_router(customer_router, prefix="/customer")
