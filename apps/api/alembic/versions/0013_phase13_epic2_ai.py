"""phase13 epic2 ai orchestration

Revision ID: 0013_phase13
Revises: 0012_phase12
Create Date: 2026-07-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_phase13"
down_revision: Union[str, None] = "0012_phase12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column(
        "ai_conversations",
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "ai_conversations",
        sa.Column("share_token", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_ai_conversations_pinned", "ai_conversations", ["pinned"])
    op.create_index("ix_ai_conversations_share_token", "ai_conversations", ["share_token"])

    op.create_table(
        "ai_request_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("tools_used", JSON, nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("prompt_preview", sa.String(length=500), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("metadata", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["ai_conversations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_request_logs_organization_id", "ai_request_logs", ["organization_id"])
    op.create_index("ix_ai_request_logs_user_id", "ai_request_logs", ["user_id"])
    op.create_index("ix_ai_request_logs_conversation_id", "ai_request_logs", ["conversation_id"])
    op.create_index("ix_ai_request_logs_action", "ai_request_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_ai_request_logs_action", table_name="ai_request_logs")
    op.drop_index("ix_ai_request_logs_conversation_id", table_name="ai_request_logs")
    op.drop_index("ix_ai_request_logs_user_id", table_name="ai_request_logs")
    op.drop_index("ix_ai_request_logs_organization_id", table_name="ai_request_logs")
    op.drop_table("ai_request_logs")
    op.drop_index("ix_ai_conversations_share_token", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_pinned", table_name="ai_conversations")
    op.drop_column("ai_conversations", "share_token")
    op.drop_column("ai_conversations", "pinned")
