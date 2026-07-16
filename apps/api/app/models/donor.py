from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.grant import Grant


class Donor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Funding partner / donor organization within a tenant."""

    __tablename__ = "donors"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_donors_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    donor_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="foundation"
    )  # bilateral | multilateral | foundation | corporate | government | individual | other
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | inactive | prospect
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(64))
    website: Mapped[Optional[str]] = mapped_column(String(512))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    grants: Mapped[list[Grant]] = relationship(
        "Grant", back_populates="donor", cascade="all, delete-orphan"
    )
