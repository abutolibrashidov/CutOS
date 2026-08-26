"""Add appointment_services table; make appointment.service_id nullable.

Revision ID: 0003
Revises: 0002_stage2_constraints
Create Date: 2026-08-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Make service_id and service_name_at_booking nullable on appointments.
    #    price_at_booking and duration_at_booking stay NOT NULL (they now hold
    #    aggregate totals).
    op.alter_column("appointments", "service_id", nullable=True)
    op.alter_column("appointments", "service_name_at_booking", nullable=True)

    # 2. Create appointment_services table
    op.create_table(
        "appointment_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name_at_booking", sa.String(255), nullable=False),
        sa.Column("price_at_booking", sa.BigInteger(), nullable=False),
        sa.Column("duration_at_booking", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["appointment_id"], ["appointments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_services_appointment_id",
        "appointment_services",
        ["appointment_id"],
    )
    op.create_index(
        "ix_appointment_services_service_id",
        "appointment_services",
        ["service_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_appointment_services_service_id", "appointment_services")
    op.drop_index("ix_appointment_services_appointment_id", "appointment_services")
    op.drop_table("appointment_services")
    op.alter_column("appointments", "service_name_at_booking", nullable=False)
    op.alter_column("appointments", "service_id", nullable=False)
