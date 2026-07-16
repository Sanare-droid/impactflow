from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class MarketplaceInstallation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Organization install of a marketplace app."""

    __tablename__ = "marketplace_installations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "app_id",
            name="uq_marketplace_installations_org_app",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_apps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="installed", index=True
    )  # installed | suspended | uninstalled
    config: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    installed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
