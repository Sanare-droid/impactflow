from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    pass


class AiConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Copilot chat thread scoped to an organization and user."""

    __tablename__ = "ai_conversations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New conversation")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | archived
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    share_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    context: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    messages: Mapped[list[AiMessage]] = relationship(
        "AiMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AiMessage.created_at",
    )


class AiMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Single message within a copilot conversation."""

    __tablename__ = "ai_messages"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # system | user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="fallback")
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    conversation: Mapped[AiConversation] = relationship(
        "AiConversation", back_populates="messages"
    )


class AiRequestLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Observability record for a single AI orchestration request.

    Never stores full AI response bodies — only truncated prompt preview,
    which tools ran, model/provider, token count, duration, and success.
    """

    __tablename__ = "ai_request_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # chat | insights | report | prediction_scan
    tools_used: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="fallback")
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prompt_preview: Mapped[Optional[str]] = mapped_column(String(500))
    error_code: Mapped[Optional[str]] = mapped_column(String(64))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
