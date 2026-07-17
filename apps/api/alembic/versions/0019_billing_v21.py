"""phase19 billing v2.1 — KES catalog fields, invoices, grace/cancel columns

Revision ID: 0019_billing_v21
Revises: 0018_phase18
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_billing_v21"
down_revision: Union[str, None] = "0018_phase18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("subscription_plans", sa.Column("max_projects", sa.Integer(), nullable=True))
    op.add_column("subscription_plans", sa.Column("api_limit", sa.Integer(), nullable=True))
    op.add_column("subscription_plans", sa.Column("ai_credits", sa.Integer(), nullable=True))
    op.add_column(
        "subscription_plans",
        sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.add_column(
        "organization_subscriptions",
        sa.Column("grace_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_subscriptions",
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("billing_period", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paystack_reference", sa.String(length=128), nullable=True),
        sa.Column("receipt_url", sa.String(length=1024), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["organization_subscriptions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="uq_billing_invoices_number"),
    )
    op.create_index(
        "ix_billing_invoices_organization_id", "billing_invoices", ["organization_id"]
    )
    op.create_index("ix_billing_invoices_status", "billing_invoices", ["status"])
    op.create_index(
        "ix_billing_invoices_paystack_reference",
        "billing_invoices",
        ["paystack_reference"],
    )


def downgrade() -> None:
    op.drop_index("ix_billing_invoices_paystack_reference", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_status", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_organization_id", table_name="billing_invoices")
    op.drop_table("billing_invoices")
    op.drop_column("organization_subscriptions", "canceled_at")
    op.drop_column("organization_subscriptions", "grace_ends_at")
    op.drop_column("subscription_plans", "recommended")
    op.drop_column("subscription_plans", "ai_credits")
    op.drop_column("subscription_plans", "api_limit")
    op.drop_column("subscription_plans", "max_projects")
