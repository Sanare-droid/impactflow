from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class SavedDashboard(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configurable analytics dashboard with widget layout."""

    __tablename__ = "saved_dashboards"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_saved_dashboards_org_code"),
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
        String(32), nullable=False, default="active", index=True
    )  # draft | active | archived
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    layout: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    widgets: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    filters: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
