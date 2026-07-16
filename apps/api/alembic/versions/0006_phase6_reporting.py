"""phase6 reports dashboards maps evidence analytics

Revision ID: 0006_phase6
Revises: 0005_phase5
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase6"
down_revision: Union[str, None] = "0005_phase5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("report_type", sa.String(64), nullable=False, server_default="progress"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("summary", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["grant_id"], ["grants.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_reports_org_code"),
    )
    op.create_index("ix_reports_organization_id", "reports", ["organization_id"])
    op.create_index("ix_reports_program_id", "reports", ["program_id"])
    op.create_index("ix_reports_project_id", "reports", ["project_id"])
    op.create_index("ix_reports_grant_id", "reports", ["grant_id"])
    op.create_index("ix_reports_code", "reports", ["code"])
    op.create_index("ix_reports_report_type", "reports", ["report_type"])
    op.create_index("ix_reports_status", "reports", ["status"])

    op.create_table(
        "saved_dashboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("layout", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("widgets", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "code", name="uq_saved_dashboards_org_code"),
    )
    op.create_index("ix_saved_dashboards_organization_id", "saved_dashboards", ["organization_id"])
    op.create_index("ix_saved_dashboards_code", "saved_dashboards", ["code"])
    op.create_index("ix_saved_dashboards_status", "saved_dashboards", ["status"])

    op.create_table(
        "map_layers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("layer_type", sa.String(64), nullable=False, server_default="sites"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("description", sa.Text()),
        sa.Column("style", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_map_layers_org_code"),
    )
    op.create_index("ix_map_layers_organization_id", "map_layers", ["organization_id"])
    op.create_index("ix_map_layers_program_id", "map_layers", ["program_id"])
    op.create_index("ix_map_layers_project_id", "map_layers", ["project_id"])
    op.create_index("ix_map_layers_code", "map_layers", ["code"])
    op.create_index("ix_map_layers_layer_type", "map_layers", ["layer_type"])
    op.create_index("ix_map_layers_status", "map_layers", ["status"])

    op.create_table(
        "map_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("layer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("feature_type", sa.String(32), nullable=False, server_default="point"),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("geometry", postgresql.JSONB()),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("community_id", postgresql.UUID(as_uuid=True)),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["layer_id"], ["map_layers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_map_features_organization_id", "map_features", ["organization_id"])
    op.create_index("ix_map_features_layer_id", "map_features", ["layer_id"])
    op.create_index("ix_map_features_community_id", "map_features", ["community_id"])

    op.create_table(
        "evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True)),
        sa.Column("monitoring_result_id", postgresql.UUID(as_uuid=True)),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True)),
        sa.Column("beneficiary_id", postgresql.UUID(as_uuid=True)),
        sa.Column("report_id", postgresql.UUID(as_uuid=True)),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("evidence_type", sa.String(64), nullable=False, server_default="document"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("description", sa.Text()),
        sa.Column("collected_on", sa.Date()),
        sa.Column("source", sa.String(255)),
        sa.Column("file_url", sa.String(1024)),
        sa.Column("file_name", sa.String(255)),
        sa.Column("mime_type", sa.String(128)),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["monitoring_result_id"], ["monitoring_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_evidence_items_org_code"),
    )
    op.create_index("ix_evidence_items_organization_id", "evidence_items", ["organization_id"])
    op.create_index("ix_evidence_items_program_id", "evidence_items", ["program_id"])
    op.create_index("ix_evidence_items_project_id", "evidence_items", ["project_id"])
    op.create_index("ix_evidence_items_indicator_id", "evidence_items", ["indicator_id"])
    op.create_index("ix_evidence_items_monitoring_result_id", "evidence_items", ["monitoring_result_id"])
    op.create_index("ix_evidence_items_evaluation_id", "evidence_items", ["evaluation_id"])
    op.create_index("ix_evidence_items_beneficiary_id", "evidence_items", ["beneficiary_id"])
    op.create_index("ix_evidence_items_report_id", "evidence_items", ["report_id"])
    op.create_index("ix_evidence_items_code", "evidence_items", ["code"])
    op.create_index("ix_evidence_items_evidence_type", "evidence_items", ["evidence_type"])
    op.create_index("ix_evidence_items_status", "evidence_items", ["status"])


def downgrade() -> None:
    op.drop_table("evidence_items")
    op.drop_table("map_features")
    op.drop_table("map_layers")
    op.drop_table("saved_dashboards")
    op.drop_table("reports")
