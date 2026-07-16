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
    from app.models.indicator import Indicator, IndicatorTarget


class MonitoringResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Actual monitoring value recorded against an indicator (and optional target)."""

    __tablename__ = "monitoring_results"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    indicator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicators.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicator_targets.id", ondelete="SET NULL"),
        index=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
    )
    reporting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date)
    period_end: Mapped[Optional[date]] = mapped_column(Date)
    actual_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    qualitative_value: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )  # draft | submitted | verified | rejected
    data_source: Mapped[Optional[str]] = mapped_column(String(255))
    location_label: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    collected_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    indicator: Mapped[Indicator] = relationship(
        "Indicator", back_populates="monitoring_results"
    )
    target: Mapped[Optional[IndicatorTarget]] = relationship(
        "IndicatorTarget", back_populates="monitoring_results"
    )
