"""phase7 ai copilot predictions narratives knowledge

Revision ID: 0007_phase7
Revises: 0006_phase6
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_phase7"
down_revision: Union[str, None] = "0006_phase6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="New conversation"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_conversations_organization_id", "ai_conversations", ["organization_id"])
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])
    op.create_index("ix_ai_conversations_status", "ai_conversations", ["status"])

    op.create_table(
        "ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(128)),
        sa.Column("provider", sa.String(64), nullable=False, server_default="fallback"),
        sa.Column("token_count", sa.Integer()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_messages_organization_id", "ai_messages", ["organization_id"])
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])

    op.create_table(
        "ai_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("prediction_type", sa.String(64), nullable=False, server_default="project_risk"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("score", sa.Numeric(5, 2), nullable=False, server_default="50"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("recommendations", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("signals", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("provider", sa.String(64), nullable=False, server_default="fallback"),
        sa.Column("model", sa.String(128)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ai_predictions_organization_id", "ai_predictions", ["organization_id"])
    op.create_index("ix_ai_predictions_program_id", "ai_predictions", ["program_id"])
    op.create_index("ix_ai_predictions_project_id", "ai_predictions", ["project_id"])
    op.create_index("ix_ai_predictions_prediction_type", "ai_predictions", ["prediction_type"])
    op.create_index("ix_ai_predictions_severity", "ai_predictions", ["severity"])
    op.create_index("ix_ai_predictions_status", "ai_predictions", ["status"])

    op.create_table(
        "ai_narratives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("report_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("narrative_type", sa.String(64), nullable=False, server_default="executive_summary"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("prompt", sa.Text()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False, server_default="fallback"),
        sa.Column("model", sa.String(128)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_ai_narratives_org_code"),
    )
    op.create_index("ix_ai_narratives_organization_id", "ai_narratives", ["organization_id"])
    op.create_index("ix_ai_narratives_program_id", "ai_narratives", ["program_id"])
    op.create_index("ix_ai_narratives_project_id", "ai_narratives", ["project_id"])
    op.create_index("ix_ai_narratives_report_id", "ai_narratives", ["report_id"])
    op.create_index("ix_ai_narratives_code", "ai_narratives", ["code"])
    op.create_index("ix_ai_narratives_narrative_type", "ai_narratives", ["narrative_type"])
    op.create_index("ix_ai_narratives_status", "ai_narratives", ["status"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="guidance"),
        sa.Column("status", sa.String(32), nullable=False, server_default="published"),
        sa.Column("summary", sa.Text()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255)),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("embedding_ref", sa.String(255)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "code", name="uq_knowledge_documents_org_code"),
    )
    op.create_index("ix_knowledge_documents_organization_id", "knowledge_documents", ["organization_id"])
    op.create_index("ix_knowledge_documents_code", "knowledge_documents", ["code"])
    op.create_index("ix_knowledge_documents_category", "knowledge_documents", ["category"])
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])


def downgrade() -> None:
    op.drop_table("knowledge_documents")
    op.drop_table("ai_narratives")
    op.drop_table("ai_predictions")
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
