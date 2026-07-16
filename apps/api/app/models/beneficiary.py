from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.community import Community
    from app.models.household import Household


class Beneficiary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual beneficiary / participant record."""

    __tablename__ = "beneficiaries"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_beneficiaries_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="SET NULL"),
        index=True,
    )
    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="SET NULL"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(120))
    sex: Mapped[Optional[str]] = mapped_column(String(32))  # female | male | other | prefer_not_to_say
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    national_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # active | inactive | deceased | duplicate
    registration_date: Mapped[Optional[date]] = mapped_column(Date)
    consent_data_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_household_head: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vulnerability_tags: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    household: Mapped[Optional[Household]] = relationship(
        "Household",
        back_populates="members",
    )
    community: Mapped[Optional[Community]] = relationship(
        "Community", back_populates="beneficiaries"
    )
    memberships: Mapped[list[BeneficiaryMembership]] = relationship(
        "BeneficiaryMembership",
        back_populates="beneficiary",
        cascade="all, delete-orphan",
    )


class BeneficiaryMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Enrollment of a beneficiary in a program / project / activity."""

    __tablename__ = "beneficiary_memberships"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("beneficiaries.id", ondelete="CASCADE"),
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
    activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="SET NULL"),
        index=True,
    )
    membership_role: Mapped[str] = mapped_column(
        String(64), nullable=False, default="participant"
    )  # participant | caregiver | household_member | other
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="enrolled", index=True
    )  # enrolled | active | graduated | exited | suspended
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    exit_reason: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    beneficiary: Mapped[Beneficiary] = relationship(
        "Beneficiary", back_populates="memberships"
    )
