from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class OrgApiKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Hashed API key for programmatic org access."""

    __tablename__ = "org_api_keys"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | revoked
    scopes: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class IntegrationConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Third-party or webhook integration configured for an organization."""

    __tablename__ = "integration_connections"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(64), nullable=False, default="webhook", index=True
    )  # webhook | kobo | odk | slack | email | sheets | custom
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | paused | error | archived
    direction: Mapped[str] = mapped_column(
        String(32), nullable=False, default="outbound"
    )  # inbound | outbound | bidirectional
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(1024))
    secret_hint: Mapped[Optional[str]] = mapped_column(String(32))
    # Never return raw secrets in API responses; store redacted/config only
    config: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    events: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class OrgBranding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """White-label branding settings for an organization (1:1)."""

    __tablename__ = "org_branding"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    tagline: Mapped[Optional[str]] = mapped_column(String(255))
    primary_color: Mapped[str] = mapped_column(String(32), nullable=False, default="#0F766E")
    secondary_color: Mapped[str] = mapped_column(String(32), nullable=False, default="#44403C")
    accent_color: Mapped[Optional[str]] = mapped_column(String(32))
    logo_url: Mapped[Optional[str]] = mapped_column(String(1024))
    favicon_url: Mapped[Optional[str]] = mapped_column(String(1024))
    login_background_url: Mapped[Optional[str]] = mapped_column(String(1024))
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    support_email: Mapped[Optional[str]] = mapped_column(String(255))
    support_url: Mapped[Optional[str]] = mapped_column(String(512))
    hide_powered_by: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
