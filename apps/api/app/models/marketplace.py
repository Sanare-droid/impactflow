from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class MarketplaceApp(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Platform catalog of installable apps / connectors."""

    __tablename__ = "marketplace_apps"
    __table_args__ = (UniqueConstraint("code", name="uq_marketplace_apps_code"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="integration", index=True
    )  # integration | analytics | data_collection | communication | finance | other
    summary: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False, default="ImpactFlow")
    pricing_tier: Mapped[str] = mapped_column(
        String(32), nullable=False, default="free"
    )  # free | standard | premium
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="published", index=True
    )  # draft | published | deprecated
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    icon_key: Mapped[Optional[str]] = mapped_column(String(64))
    config_schema: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
