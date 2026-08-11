"""
Central import for all SQLAlchemy models.

Importing this module guarantees that all models are registered with
SQLAlchemy's metadata before Alembic autogenerate runs its introspection.
"""

from app.models.appointment import Appointment, AppointmentSource, AppointmentStatus
from app.models.barber import Barber
from app.models.barber_customer import BarberCustomer
from app.models.base import UUIDBase
from app.models.blocked_time import BlockedTime
from app.models.customer import Customer
from app.models.expense import Expense
from app.models.location import Location
from app.models.schedule import WorkingSchedule
from app.models.service import Service

__all__ = [
    "UUIDBase",
    "Location",
    "Barber",
    "Customer",
    "BarberCustomer",
    "Service",
    "WorkingSchedule",
    "BlockedTime",
    "Appointment",
    "AppointmentStatus",
    "AppointmentSource",
    "Expense",
]
