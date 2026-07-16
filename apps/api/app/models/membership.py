from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.role import Role
    from app.models.user import User


class OrganizationMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Links a user to an organization with a role. Enforces tenant isolation."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", name="uq_membership_org_user"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )  # invited, active, suspended, left
    invited_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="memberships"
    )
    user: Mapped[User] = relationship("User", back_populates="memberships")
    role: Mapped[Role] = relationship("Role", back_populates="memberships")
