"""phase4 meal theory of change logframe indicators monitoring evaluation

Revision ID: 0004_phase4
Revises: 0003_phase3
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase4"
down_revision: Union[str, None] = "0003_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "theories_of_change",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("goal_statement", sa.Text()),
        sa.Column("problem_statement", sa.Text()),
        sa.Column("assumptions", sa.Text()),
        sa.Column("success_criteria", sa.Text()),
        sa.Column("pathways", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_theories_of_change_org_code"),
    )
    op.create_index("ix_theories_of_change_organization_id", "theories_of_change", ["organization_id"])
    op.create_index("ix_theories_of_change_program_id", "theories_of_change", ["program_id"])
    op.create_index("ix_theories_of_change_project_id", "theories_of_change", ["project_id"])
    op.create_index("ix_theories_of_change_code", "theories_of_change", ["code"])
    op.create_index("ix_theories_of_change_status", "theories_of_change", ["status"])

    op.create_table(
        "logframes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theory_of_change_id", postgresql.UUID(as_uuid=True)),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theory_of_change_id"], ["theories_of_change.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_logframes_org_code"),
    )
    op.create_index("ix_logframes_organization_id", "logframes", ["organization_id"])
    op.create_index("ix_logframes_theory_of_change_id", "logframes", ["theory_of_change_id"])
    op.create_index("ix_logframes_program_id", "logframes", ["program_id"])
    op.create_index("ix_logframes_project_id", "logframes", ["project_id"])
    op.create_index("ix_logframes_code", "logframes", ["code"])
    op.create_index("ix_logframes_status", "logframes", ["status"])

    op.create_table(
        "logframe_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("logframe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("level", sa.String(32), nullable=False),
        sa.Column("code", sa.String(64)),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("assumptions", sa.Text()),
        sa.Column("means_of_verification", sa.Text()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["logframe_id"], ["logframes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["logframe_results.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_logframe_results_organization_id", "logframe_results", ["organization_id"])
    op.create_index("ix_logframe_results_logframe_id", "logframe_results", ["logframe_id"])
    op.create_index("ix_logframe_results_parent_id", "logframe_results", ["parent_id"])
    op.create_index("ix_logframe_results_level", "logframe_results", ["level"])

    op.create_table(
        "indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("logframe_result_id", postgresql.UUID(as_uuid=True)),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("level", sa.String(32), nullable=False, server_default="outcome"),
        sa.Column("measure_type", sa.String(32), nullable=False, server_default="quantitative"),
        sa.Column("unit", sa.String(64)),
        sa.Column("direction", sa.String(32), nullable=False, server_default="increase"),
        sa.Column("collection_method", sa.String(128)),
        sa.Column("frequency", sa.String(64)),
        sa.Column("baseline_value", sa.Numeric(18, 4)),
        sa.Column("baseline_date", sa.Date()),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("disaggregation", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["logframe_result_id"], ["logframe_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_indicators_org_code"),
    )
    op.create_index("ix_indicators_organization_id", "indicators", ["organization_id"])
    op.create_index("ix_indicators_program_id", "indicators", ["program_id"])
    op.create_index("ix_indicators_project_id", "indicators", ["project_id"])
    op.create_index("ix_indicators_logframe_result_id", "indicators", ["logframe_result_id"])
    op.create_index("ix_indicators_activity_id", "indicators", ["activity_id"])
    op.create_index("ix_indicators_code", "indicators", ["code"])
    op.create_index("ix_indicators_level", "indicators", ["level"])
    op.create_index("ix_indicators_status", "indicators", ["status"])

    op.create_table(
        "indicator_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_label", sa.String(128), nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("target_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_indicator_targets_organization_id", "indicator_targets", ["organization_id"])
    op.create_index("ix_indicator_targets_indicator_id", "indicator_targets", ["indicator_id"])
    op.create_index("ix_indicator_targets_status", "indicator_targets", ["status"])

    op.create_table(
        "monitoring_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reporting_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("actual_value", sa.Numeric(18, 4)),
        sa.Column("qualitative_value", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("data_source", sa.String(255)),
        sa.Column("location_label", sa.String(255)),
        sa.Column("notes", sa.Text()),
        sa.Column("collected_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("verified_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["indicator_targets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_monitoring_results_organization_id", "monitoring_results", ["organization_id"])
    op.create_index("ix_monitoring_results_indicator_id", "monitoring_results", ["indicator_id"])
    op.create_index("ix_monitoring_results_target_id", "monitoring_results", ["target_id"])
    op.create_index("ix_monitoring_results_project_id", "monitoring_results", ["project_id"])
    op.create_index("ix_monitoring_results_reporting_date", "monitoring_results", ["reporting_date"])
    op.create_index("ix_monitoring_results_status", "monitoring_results", ["status"])

    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("evaluation_type", sa.String(32), nullable=False, server_default="midline"),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("evaluator_name", sa.String(255)),
        sa.Column("objectives", sa.Text()),
        sa.Column("methodology", sa.Text()),
        sa.Column("key_findings", sa.Text()),
        sa.Column("recommendations", sa.Text()),
        sa.Column("lessons_learned", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_evaluations_org_code"),
    )
    op.create_index("ix_evaluations_organization_id", "evaluations", ["organization_id"])
    op.create_index("ix_evaluations_program_id", "evaluations", ["program_id"])
    op.create_index("ix_evaluations_project_id", "evaluations", ["project_id"])
    op.create_index("ix_evaluations_code", "evaluations", ["code"])
    op.create_index("ix_evaluations_evaluation_type", "evaluations", ["evaluation_type"])
    op.create_index("ix_evaluations_status", "evaluations", ["status"])


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("monitoring_results")
    op.drop_table("indicator_targets")
    op.drop_table("indicators")
    op.drop_table("logframe_results")
    op.drop_table("logframes")
    op.drop_table("theories_of_change")
