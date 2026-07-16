"""phase5 beneficiaries households communities memberships

Revision ID: 0005_phase5
Revises: 0004_phase4
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase5"
down_revision: Union[str, None] = "0004_phase4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "communities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("community_type", sa.String(64), nullable=False, server_default="village"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("country_code", sa.String(2)),
        sa.Column("region", sa.String(128)),
        sa.Column("district", sa.String(128)),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("population_estimate", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["communities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_communities_org_code"),
    )
    op.create_index("ix_communities_organization_id", "communities", ["organization_id"])
    op.create_index("ix_communities_parent_id", "communities", ["parent_id"])
    op.create_index("ix_communities_code", "communities", ["code"])
    op.create_index("ix_communities_community_type", "communities", ["community_type"])
    op.create_index("ix_communities_status", "communities", ["status"])

    op.create_table(
        "households",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("address", sa.Text()),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("household_size", sa.Integer()),
        sa.Column("poverty_status", sa.String(64)),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_households_org_code"),
    )
    op.create_index("ix_households_organization_id", "households", ["organization_id"])
    op.create_index("ix_households_community_id", "households", ["community_id"])
    op.create_index("ix_households_code", "households", ["code"])
    op.create_index("ix_households_status", "households", ["status"])

    op.create_table(
        "beneficiaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("household_id", postgresql.UUID(as_uuid=True)),
        sa.Column("community_id", postgresql.UUID(as_uuid=True)),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=False),
        sa.Column("middle_name", sa.String(120)),
        sa.Column("sex", sa.String(32)),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("national_id", sa.String(64)),
        sa.Column("phone", sa.String(64)),
        sa.Column("email", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("registration_date", sa.Date()),
        sa.Column("consent_data_use", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("consent_photo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_household_head", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("vulnerability_tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("notes", sa.Text()),
        sa.Column("photo_url", sa.String(512)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_beneficiaries_org_code"),
    )
    op.create_index("ix_beneficiaries_organization_id", "beneficiaries", ["organization_id"])
    op.create_index("ix_beneficiaries_household_id", "beneficiaries", ["household_id"])
    op.create_index("ix_beneficiaries_community_id", "beneficiaries", ["community_id"])
    op.create_index("ix_beneficiaries_code", "beneficiaries", ["code"])
    op.create_index("ix_beneficiaries_national_id", "beneficiaries", ["national_id"])
    op.create_index("ix_beneficiaries_status", "beneficiaries", ["status"])

    op.create_table(
        "beneficiary_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("beneficiary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("membership_role", sa.String(64), nullable=False, server_default="participant"),
        sa.Column("status", sa.String(32), nullable=False, server_default="enrolled"),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("exit_reason", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_beneficiary_memberships_organization_id", "beneficiary_memberships", ["organization_id"])
    op.create_index("ix_beneficiary_memberships_beneficiary_id", "beneficiary_memberships", ["beneficiary_id"])
    op.create_index("ix_beneficiary_memberships_program_id", "beneficiary_memberships", ["program_id"])
    op.create_index("ix_beneficiary_memberships_project_id", "beneficiary_memberships", ["project_id"])
    op.create_index("ix_beneficiary_memberships_activity_id", "beneficiary_memberships", ["activity_id"])
    op.create_index("ix_beneficiary_memberships_status", "beneficiary_memberships", ["status"])


def downgrade() -> None:
    op.drop_table("beneficiary_memberships")
    op.drop_table("beneficiaries")
    op.drop_table("households")
    op.drop_table("communities")
