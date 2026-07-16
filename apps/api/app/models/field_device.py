from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class FieldDevice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered mobile field device for sync monitoring and remote control."""

    __tablename__ = "field_devices"
    __table_args__ = (
        UniqueConstraint("organization_id", "device_key", name="uq_field_devices_org_key"),
    )

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
    device_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    app_version: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | deactivated | revoked
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    push_token: Mapped[Optional[str]] = mapped_column(String(512))
    storage_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_uploads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    organization: Mapped[Organization] = relationship("Organization")
    user: Mapped[User] = relationship("User")
    sync_sessions: Mapped[list[SyncSession]] = relationship(
        "SyncSession", back_populates="device", cascade="all, delete-orphan"
    )


class SyncSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One sync run from a field device — audit trail and progress tracking."""

    __tablename__ = "sync_sessions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("field_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="running", index=True
    )  # running | completed | failed | partial
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pushed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pulled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    sync_token: Mapped[Optional[str]] = mapped_column(String(64))
    client_version: Mapped[Optional[str]] = mapped_column(String(64))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    device: Mapped[FieldDevice] = relationship("FieldDevice", back_populates="sync_sessions")


class SyncMutationLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Idempotency log for batch push mutations from field devices."""

    __tablename__ = "sync_mutation_logs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "client_mutation_id",
            name="uq_sync_mutations_org_client",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("field_devices.id", ondelete="SET NULL"),
        index=True,
    )
    client_mutation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    op: Mapped[str] = mapped_column(String(32), nullable=False)
    local_id: Mapped[Optional[str]] = mapped_column(String(128))
    server_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="applied"
    )  # applied | duplicate | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)


class SyncConflictLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Server-wins conflict record — local copy preserved on device, logged server-side."""

    __tablename__ = "sync_conflict_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("field_devices.id", ondelete="SET NULL"),
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    local_id: Mapped[Optional[str]] = mapped_column(String(128))
    server_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    resolution: Mapped[str] = mapped_column(String(32), nullable=False, default="server_wins")
    local_snapshot: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    server_snapshot: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)


class MediaUploadRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Queued media upload from a field device — monitored on web dashboard."""

    __tablename__ = "media_upload_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "client_mutation_id",
            name="uq_media_uploads_org_client",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("field_devices.id", ondelete="SET NULL"),
        index=True,
    )
    client_mutation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )  # pending | uploaded | failed
    remote_url: Mapped[Optional[str]] = mapped_column(String(1024))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
