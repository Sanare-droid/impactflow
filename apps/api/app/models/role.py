from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.permission import RolePermission
    from app.models.membership import OrganizationMembership


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Organization-scoped role (or system role when organization_id is null)."""

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_roles_org_slug"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions_config: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    organization: Mapped[Optional[Organization]] = relationship(
        "Organization", back_populates="roles"
    )
    role_permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership", back_populates="role"
    )

    def __repr__(self) -> str:
        return f"<Role {self.slug}>"
