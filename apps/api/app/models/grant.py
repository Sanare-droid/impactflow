from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.budget import Budget
    from app.models.donor import Donor
    from app.models.finance import FinanceTransaction


class Grant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Funding agreement linked to a donor and optionally program/project."""

    __tablename__ = "grants"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_grants_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    donor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donors.id", ondelete="RESTRICT"),
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
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pipeline", index=True
    )  # pipeline | awarded | active | closed | rejected
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    amount_awarded: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    amount_received: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    agreement_reference: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    donor: Mapped[Donor] = relationship("Donor", back_populates="grants")
    budgets: Mapped[list[Budget]] = relationship(
        "Budget", back_populates="grant", cascade="all, delete-orphan"
    )
    transactions: Mapped[list[FinanceTransaction]] = relationship(
        "FinanceTransaction", back_populates="grant"
    )
