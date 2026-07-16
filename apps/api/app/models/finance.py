from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.budget import Budget
    from app.models.grant import Grant


class FinanceTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Income, expense, commitment, or transfer against grants/budgets/projects."""

    __tablename__ = "finance_transactions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("grants.id", ondelete="SET NULL"),
        index=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
    )
    budget_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budgets.id", ondelete="SET NULL"),
        index=True,
    )
    budget_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_lines.id", ondelete="SET NULL"),
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # income | expense | commitment | transfer
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="posted", index=True
    )  # draft | posted | void
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    reference: Mapped[Optional[str]] = mapped_column(String(128))
    category: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    grant: Mapped[Optional[Grant]] = relationship("Grant", back_populates="transactions")
    budget: Mapped[Optional[Budget]] = relationship("Budget", back_populates="transactions")
