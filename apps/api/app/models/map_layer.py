from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    pass


class MapLayer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Named map layer (sites, coverage, hazards, etc.)."""

    __tablename__ = "map_layers"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_map_layers_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="SET NULL"),
        index=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    layer_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="sites", index=True
    )  # sites | coverage | communities | hazards | custom
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # draft | active | archived
    description: Mapped[Optional[str]] = mapped_column(Text)
    style: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    features: Mapped[list[MapFeature]] = relationship(
        "MapFeature",
        back_populates="layer",
        cascade="all, delete-orphan",
        order_by="MapFeature.sort_order",
    )


class MapFeature(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Point/polygon feature belonging to a map layer."""

    __tablename__ = "map_features"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    layer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("map_layers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="point"
    )  # point | polygon | line
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    geometry: Mapped[Optional[dict]] = mapped_column(JSONType)
    properties: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="SET NULL"),
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    layer: Mapped[MapLayer] = relationship("MapLayer", back_populates="features")
