"""phase12 epic1 dynamic forms engine

Revision ID: 0012_phase12
Revises: 0011_phase11
Create Date: 2026-07-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_phase12"
down_revision: Union[str, None] = "0011_phase11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("surveys", sa.Column("category", sa.String(length=128), nullable=True))
    op.add_column("surveys", sa.Column("activity_id", sa.UUID(), nullable=True))
    op.add_column(
        "surveys",
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("surveys", sa.Column("response_limit", sa.Integer(), nullable=True))
    op.add_column("surveys", sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("surveys", sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("surveys", sa.Column("cloned_from_id", sa.UUID(), nullable=True))
    op.create_index("ix_surveys_category", "surveys", ["category"])
    op.create_index("ix_surveys_activity_id", "surveys", ["activity_id"])
    op.create_index("ix_surveys_cloned_from_id", "surveys", ["cloned_from_id"])
    op.create_foreign_key(
        "fk_surveys_activity_id", "surveys", "activities", ["activity_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_surveys_cloned_from_id",
        "surveys",
        "surveys",
        ["cloned_from_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("survey_versions", sa.Column("changelog", sa.Text(), nullable=True))

    op.create_table(
        "survey_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by_id", sa.UUID(), nullable=True),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_survey_assignments_organization_id", "survey_assignments", ["organization_id"])
    op.create_index("ix_survey_assignments_survey_id", "survey_assignments", ["survey_id"])
    op.create_index("ix_survey_assignments_target_type", "survey_assignments", ["target_type"])
    op.create_index("ix_survey_assignments_target_id", "survey_assignments", ["target_id"])
    op.create_index("ix_survey_assignments_status", "survey_assignments", ["status"])

    op.add_column("survey_responses", sa.Column("household_id", sa.UUID(), nullable=True))
    op.add_column("survey_responses", sa.Column("program_id", sa.UUID(), nullable=True))
    op.add_column("survey_responses", sa.Column("project_id", sa.UUID(), nullable=True))
    op.add_column("survey_responses", sa.Column("activity_id", sa.UUID(), nullable=True))
    op.add_column("survey_responses", sa.Column("assignment_id", sa.UUID(), nullable=True))
    op.add_column("survey_responses", sa.Column("client_mutation_id", sa.String(length=64), nullable=True))
    op.add_column("survey_responses", sa.Column("location", JSON, nullable=True))
    op.add_column("survey_responses", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_survey_responses_household_id", "survey_responses", ["household_id"])
    op.create_index("ix_survey_responses_program_id", "survey_responses", ["program_id"])
    op.create_index("ix_survey_responses_project_id", "survey_responses", ["project_id"])
    op.create_index("ix_survey_responses_activity_id", "survey_responses", ["activity_id"])
    op.create_index("ix_survey_responses_assignment_id", "survey_responses", ["assignment_id"])
    op.create_index("ix_survey_responses_client_mutation_id", "survey_responses", ["client_mutation_id"])
    op.create_foreign_key(
        "fk_survey_responses_household_id",
        "survey_responses",
        "households",
        ["household_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_survey_responses_program_id",
        "survey_responses",
        "programs",
        ["program_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_survey_responses_project_id",
        "survey_responses",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_survey_responses_activity_id",
        "survey_responses",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_survey_responses_assignment_id",
        "survey_responses",
        "survey_assignments",
        ["assignment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_survey_responses_org_client_mutation",
        "survey_responses",
        ["organization_id", "client_mutation_id"],
    )

    op.create_table(
        "survey_answers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("response_id", sa.UUID(), nullable=False),
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.String(length=128), nullable=False),
        sa.Column("field_type", sa.String(length=64), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_number", sa.String(length=64), nullable=True),
        sa.Column("value_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["response_id"], ["survey_responses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_id", "field_id", name="uq_survey_answers_response_field"),
    )
    op.create_index("ix_survey_answers_organization_id", "survey_answers", ["organization_id"])
    op.create_index("ix_survey_answers_response_id", "survey_answers", ["response_id"])
    op.create_index("ix_survey_answers_survey_id", "survey_answers", ["survey_id"])
    op.create_index("ix_survey_answers_field_id", "survey_answers", ["field_id"])

    op.create_table(
        "survey_response_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("response_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.String(length=128), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("storage_url", sa.Text(), nullable=False),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["response_id"], ["survey_responses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_survey_response_attachments_organization_id",
        "survey_response_attachments",
        ["organization_id"],
    )
    op.create_index(
        "ix_survey_response_attachments_response_id",
        "survey_response_attachments",
        ["response_id"],
    )
    op.create_index(
        "ix_survey_response_attachments_field_id",
        "survey_response_attachments",
        ["field_id"],
    )


def downgrade() -> None:
    op.drop_table("survey_response_attachments")
    op.drop_table("survey_answers")
    op.drop_constraint("uq_survey_responses_org_client_mutation", "survey_responses", type_="unique")
    op.drop_constraint("fk_survey_responses_assignment_id", "survey_responses", type_="foreignkey")
    op.drop_constraint("fk_survey_responses_activity_id", "survey_responses", type_="foreignkey")
    op.drop_constraint("fk_survey_responses_project_id", "survey_responses", type_="foreignkey")
    op.drop_constraint("fk_survey_responses_program_id", "survey_responses", type_="foreignkey")
    op.drop_constraint("fk_survey_responses_household_id", "survey_responses", type_="foreignkey")
    op.drop_index("ix_survey_responses_client_mutation_id", table_name="survey_responses")
    op.drop_index("ix_survey_responses_assignment_id", table_name="survey_responses")
    op.drop_index("ix_survey_responses_activity_id", table_name="survey_responses")
    op.drop_index("ix_survey_responses_project_id", table_name="survey_responses")
    op.drop_index("ix_survey_responses_program_id", table_name="survey_responses")
    op.drop_index("ix_survey_responses_household_id", table_name="survey_responses")
    op.drop_column("survey_responses", "submitted_at")
    op.drop_column("survey_responses", "location")
    op.drop_column("survey_responses", "client_mutation_id")
    op.drop_column("survey_responses", "assignment_id")
    op.drop_column("survey_responses", "activity_id")
    op.drop_column("survey_responses", "project_id")
    op.drop_column("survey_responses", "program_id")
    op.drop_column("survey_responses", "household_id")
    op.drop_table("survey_assignments")
    op.drop_column("survey_versions", "changelog")
    op.drop_constraint("fk_surveys_cloned_from_id", "surveys", type_="foreignkey")
    op.drop_constraint("fk_surveys_activity_id", "surveys", type_="foreignkey")
    op.drop_index("ix_surveys_cloned_from_id", table_name="surveys")
    op.drop_index("ix_surveys_activity_id", table_name="surveys")
    op.drop_index("ix_surveys_category", table_name="surveys")
    op.drop_column("surveys", "cloned_from_id")
    op.drop_column("surveys", "ends_at")
    op.drop_column("surveys", "starts_at")
    op.drop_column("surveys", "response_limit")
    op.drop_column("surveys", "is_anonymous")
    op.drop_column("surveys", "activity_id")
    op.drop_column("surveys", "category")
