"""Survey / dynamic form models for field data collection."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class Survey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Survey definition (points at current published version)."""

    __tablename__ = "surveys"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_surveys_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )  # draft | published | archived
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="SET NULL"), index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class SurveyVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable JSON schema snapshot for a survey version."""

    __tablename__ = "survey_versions"
    __table_args__ = (
        UniqueConstraint("survey_id", "version", name="uq_survey_versions_survey_version"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_: Mapped[dict] = mapped_column("schema", JSONType, default=dict, nullable=False)
    # schema shape: { "fields": [ { "id", "type", "label", "required", "options?" } ] }
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))


class SurveyResponse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Submitted answers for a survey version."""

    __tablename__ = "survey_responses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    survey_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("survey_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="submitted", index=True
    )  # draft | submitted | verified
    answers: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    respondent_name: Mapped[Optional[str]] = mapped_column(String(255))
    beneficiary_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("beneficiaries.id", ondelete="SET NULL"), index=True
    )
    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="SET NULL"), index=True
    )
    submitted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
