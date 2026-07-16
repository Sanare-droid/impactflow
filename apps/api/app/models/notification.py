from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """In-app notification for a user within an organization."""

    __tablename__ = "notifications"

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
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text)
    link: Mapped[Optional[str]] = mapped_column(String(512))
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="info")
    # info | success | warning | critical
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unread", index=True
    )  # unread | read | archived
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resource_type: Mapped[Optional[str]] = mapped_column(String(64))
    resource_id: Mapped[Optional[str]] = mapped_column(String(64))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class WebhookDelivery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Outbound webhook / Slack delivery attempt log."""

    __tablename__ = "webhook_deliveries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )  # pending | processing | delivered | failed | dead
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    response_status: Mapped[Optional[int]] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(64))
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(1024))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
