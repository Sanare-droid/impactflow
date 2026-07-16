"""phase8 marketplace integrations api keys white label

Revision ID: 0008_phase8
Revises: 0007_phase7
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_phase8"
down_revision: Union[str, None] = "0007_phase7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_apps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="integration"),
        sa.Column("summary", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("publisher", sa.String(255), nullable=False, server_default="ImpactFlow"),
        sa.Column("pricing_tier", sa.String(32), nullable=False, server_default="free"),
        sa.Column("status", sa.String(32), nullable=False, server_default="published"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("icon_key", sa.String(64)),
        sa.Column("config_schema", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_marketplace_apps_code"),
    )
    op.create_index("ix_marketplace_apps_code", "marketplace_apps", ["code"])
    op.create_index("ix_marketplace_apps_category", "marketplace_apps", ["category"])
    op.create_index("ix_marketplace_apps_status", "marketplace_apps", ["status"])

    op.create_table(
        "marketplace_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("app_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="installed"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text()),
        sa.Column("installed_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["app_id"], ["marketplace_apps.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "app_id", name="uq_marketplace_installations_org_app"),
    )
    op.create_index("ix_marketplace_installations_organization_id", "marketplace_installations", ["organization_id"])
    op.create_index("ix_marketplace_installations_app_id", "marketplace_installations", ["app_id"])
    op.create_index("ix_marketplace_installations_status", "marketplace_installations", ["status"])

    op.create_table(
        "org_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_org_api_keys_organization_id", "org_api_keys", ["organization_id"])
    op.create_index("ix_org_api_keys_key_prefix", "org_api_keys", ["key_prefix"])
    op.create_index("ix_org_api_keys_status", "org_api_keys", ["status"])

    op.create_table(
        "integration_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False, server_default="webhook"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("direction", sa.String(32), nullable=False, server_default="outbound"),
        sa.Column("endpoint_url", sa.String(1024)),
        sa.Column("secret_hint", sa.String(32)),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("events", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_integration_connections_organization_id", "integration_connections", ["organization_id"])
    op.create_index("ix_integration_connections_provider", "integration_connections", ["provider"])
    op.create_index("ix_integration_connections_status", "integration_connections", ["status"])

    op.create_table(
        "org_branding",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(255)),
        sa.Column("tagline", sa.String(255)),
        sa.Column("primary_color", sa.String(32), nullable=False, server_default="#0F766E"),
        sa.Column("secondary_color", sa.String(32), nullable=False, server_default="#44403C"),
        sa.Column("accent_color", sa.String(32)),
        sa.Column("logo_url", sa.String(1024)),
        sa.Column("favicon_url", sa.String(1024)),
        sa.Column("login_background_url", sa.String(1024)),
        sa.Column("custom_domain", sa.String(255)),
        sa.Column("support_email", sa.String(255)),
        sa.Column("support_url", sa.String(512)),
        sa.Column("hide_powered_by", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", name="uq_org_branding_organization_id"),
    )
    op.create_index("ix_org_branding_organization_id", "org_branding", ["organization_id"])
    op.create_index("ix_org_branding_custom_domain", "org_branding", ["custom_domain"])


def downgrade() -> None:
    op.drop_table("org_branding")
    op.drop_table("integration_connections")
    op.drop_table("org_api_keys")
    op.drop_table("marketplace_installations")
    op.drop_table("marketplace_apps")
