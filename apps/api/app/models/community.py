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
    from app.models.beneficiary import Beneficiary
    from app.models.household import Household


class Community(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Geographic or administrative community / locality."""

    __tablename__ = "communities"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_communities_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    community_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="village", index=True
    )  # village | camp | ward | district | settlement | other
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | inactive | archived
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    region: Mapped[Optional[str]] = mapped_column(String(128))
    district: Mapped[Optional[str]] = mapped_column(String(128))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    population_estimate: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    households: Mapped[list[Household]] = relationship(
        "Household", back_populates="community"
    )
    beneficiaries: Mapped[list[Beneficiary]] = relationship(
        "Beneficiary", back_populates="community"
    )
