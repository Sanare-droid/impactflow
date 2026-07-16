"""Epic 6 — integration hub models (extends Phase 8 IntegrationConnection)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class ConnectorSyncJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Background sync run for a connector / integration connection."""

    __tablename__ = "connector_sync_jobs"

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
    connector_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )  # pending | running | completed | failed | cancelled
    direction: Mapped[str] = mapped_column(String(32), nullable=False, default="pull")
    mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="incremental"
    )  # full | incremental | dry_run
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    cursor: Mapped[Optional[str]] = mapped_column(String(255))
    result: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))


class FieldMappingProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable field mapping between ImpactFlow entities and external systems."""

    __tablename__ = "field_mapping_profiles"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", name="uq_field_mapping_profiles_org_code"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="beneficiary", index=True
    )  # beneficiary | program | project | activity | indicator | survey | community
    connector_code: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    mappings: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    transformations: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    defaults: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    validation_rules: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class PluginManifest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Marketplace / plugin foundation — register extensibility hooks without core edits."""

    __tablename__ = "plugin_manifests"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_plugin_manifests_code_version"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # null = system plugin
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    # Extension points the plugin registers
    routes: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    events: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    ui_panels: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    workflow_actions: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    ai_tools: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    reports: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    dashboards: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    mobile_features: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    marketplace_app_code: Mapped[Optional[str]] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class ApiUsageLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Lightweight API key usage analytics for the API Management portal."""

    __tablename__ = "api_usage_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("org_api_keys.id", ondelete="SET NULL"),
        index=True,
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
