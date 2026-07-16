from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.membership import OrganizationMembership
    from app.models.role import Role
    from app.models.user import User


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tenant root. All business data is scoped to an organization."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255))
    organization_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="ngo"
    )  # ngo, ingo, foundation, government, un, donor, etc.
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512))
    website: Mapped[Optional[str]] = mapped_column(String(512))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    settings: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    roles: Mapped[list[Role]] = relationship(
        "Role", back_populates="organization", cascade="all, delete-orphan"
    )
    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="primary_organization",
        foreign_keys="User.primary_organization_id",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"
