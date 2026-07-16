"""Epic 5 — report templates and version history (extends Phase 6 Report model)."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class ReportTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable donor/executive report template — cloneable per organization."""

    __tablename__ = "report_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_report_templates_org_code"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # null = system built-in
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="generic", index=True
    )  # generic | usaid | eu | world_bank | un | foundation | government | csr
    report_type: Mapped[str] = mapped_column(String(64), nullable=False, default="donor")
    narrative_style: Mapped[str] = mapped_column(String(64), nullable=False, default="formal")
    sections: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    required_metrics: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    branding: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    export_preferences: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    cloned_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_templates.id", ondelete="SET NULL")
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class ReportVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable snapshot of a report for revision history."""

    __tablename__ = "report_versions"
    __table_args__ = (
        UniqueConstraint("report_id", "version", name="uq_report_versions_report_version"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text)
    sections: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    changelog: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    citations: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
