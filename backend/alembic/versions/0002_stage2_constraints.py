"""Add Stage 2 data-integrity constraints.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint("ck_services_price_nonnegative", "services", "price_uzs >= 0")
    op.create_check_constraint("ck_services_duration_positive", "services", "duration_minutes > 0")
    op.create_check_constraint("ck_working_schedules_weekday", "working_schedules", "weekday BETWEEN 0 AND 6")
    op.create_check_constraint("ck_working_schedules_time_order", "working_schedules", "end_time > start_time")
    op.create_check_constraint("ck_blocked_times_time_order", "blocked_times", "end_at > start_at")
    op.create_check_constraint("ck_expenses_amount_nonnegative", "expenses", "amount_uzs >= 0")
    op.create_check_constraint("ck_appointments_time_order", "appointments", "end_at > start_at")
    op.create_check_constraint("ck_appointments_price_nonnegative", "appointments", "price_at_booking >= 0")
    op.create_check_constraint("ck_appointments_duration_positive", "appointments", "duration_at_booking > 0")


def downgrade() -> None:
    op.drop_constraint("ck_appointments_duration_positive", "appointments", type_="check")
    op.drop_constraint("ck_appointments_price_nonnegative", "appointments", type_="check")
    op.drop_constraint("ck_appointments_time_order", "appointments", type_="check")
    op.drop_constraint("ck_expenses_amount_nonnegative", "expenses", type_="check")
    op.drop_constraint("ck_blocked_times_time_order", "blocked_times", type_="check")
    op.drop_constraint("ck_working_schedules_time_order", "working_schedules", type_="check")
    op.drop_constraint("ck_working_schedules_weekday", "working_schedules", type_="check")
    op.drop_constraint("ck_services_duration_positive", "services", type_="check")
    op.drop_constraint("ck_services_price_nonnegative", "services", type_="check")
