"""phase18 epic7 enterprise saas — billing, flags, domains, sso, backups, onboarding, locales

Revision ID: 0018_phase18
Revises: 0017_phase17
Create Date: 2026-07-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_phase18"
down_revision: Union[str, None] = "0017_phase17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("billing_period", sa.String(length=16), nullable=False),
        sa.Column("price_monthly", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_annual", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("seat_limit", sa.Integer(), nullable=True),
        sa.Column("storage_gb", sa.Integer(), nullable=True),
        sa.Column("trial_days", sa.Integer(), nullable=False),
        sa.Column("features", JSON, nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_subscription_plans_code", "subscription_plans", ["code"])
    op.create_index("ix_subscription_plans_tier", "subscription_plans", ["tier"])

    op.create_table(
        "organization_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("billing_period", sa.String(length=16), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("coupon_code", sa.String(length=64), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_org_subscriptions_org"),
    )
    op.create_index(
        "ix_organization_subscriptions_organization_id",
        "organization_subscriptions",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_subscriptions_plan_id", "organization_subscriptions", ["plan_id"]
    )
    op.create_index(
        "ix_organization_subscriptions_status", "organization_subscriptions", ["status"]
    )

    op.create_table(
        "feature_flags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_enabled", sa.Boolean(), nullable=False),
        sa.Column("rules", JSON, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_feature_flags_code"),
    )
    op.create_index("ix_feature_flags_code", "feature_flags", ["code"])

    op.create_table(
        "organization_domains",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("verification_token", sa.String(length=128), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ssl_status", sa.String(length=32), nullable=False),
        sa.Column("dns_records", JSON, nullable=False),
        sa.Column("redirect_to_primary", sa.Boolean(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname", name="uq_organization_domains_hostname"),
    )
    op.create_index(
        "ix_organization_domains_organization_id", "organization_domains", ["organization_id"]
    )
    op.create_index("ix_organization_domains_hostname", "organization_domains", ["hostname"])
    op.create_index("ix_organization_domains_status", "organization_domains", ["status"])

    op.create_table(
        "sso_configurations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("config", JSON, nullable=False),
        sa.Column("secrets", JSON, nullable=False),
        sa.Column("enforce_sso", sa.Boolean(), nullable=False),
        sa.Column("scim_enabled", sa.Boolean(), nullable=False),
        sa.Column("allowed_domains", JSON, nullable=False),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "provider", name="uq_sso_org_provider"),
    )
    op.create_index(
        "ix_sso_configurations_organization_id", "sso_configurations", ["organization_id"]
    )

    op.create_table(
        "tenant_backups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("backup_type", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("storage_uri", sa.String(length=1024), nullable=True),
        sa.Column("include", JSON, nullable=False),
        sa.Column("manifest", JSON, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_backups_organization_id", "tenant_backups", ["organization_id"])
    op.create_index("ix_tenant_backups_status", "tenant_backups", ["status"])

    op.create_table(
        "onboarding_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=64), nullable=False),
        sa.Column("checklist", JSON, nullable=False),
        sa.Column("sector", sa.String(length=128), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("theme_preset", sa.String(length=64), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_onboarding_states_org"),
    )
    op.create_index(
        "ix_onboarding_states_organization_id", "onboarding_states", ["organization_id"]
    )
    op.create_index("ix_onboarding_states_status", "onboarding_states", ["status"])

    op.create_table(
        "localization_packs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("native_name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("coverage_pct", sa.Integer(), nullable=False),
        sa.Column("strings", JSON, nullable=False),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("locale", "version", name="uq_localization_packs_locale_version"),
    )
    op.create_index("ix_localization_packs_locale", "localization_packs", ["locale"])


def downgrade() -> None:
    op.drop_table("localization_packs")
    op.drop_table("onboarding_states")
    op.drop_table("tenant_backups")
    op.drop_table("sso_configurations")
    op.drop_table("organization_domains")
    op.drop_table("feature_flags")
    op.drop_table("organization_subscriptions")
    op.drop_table("subscription_plans")
