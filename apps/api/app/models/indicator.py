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
    from app.models.logframe import LogframeResult
    from app.models.monitoring import MonitoringResult


class Indicator(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Measurable indicator used for MEAL tracking."""

    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_indicators_org_code"),
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
    logframe_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("logframe_results.id", ondelete="SET NULL"),
        index=True,
    )
    activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="outcome", index=True
    )  # impact | outcome | output | process
    measure_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="quantitative"
    )  # quantitative | qualitative
    unit: Mapped[Optional[str]] = mapped_column(String(64))
    direction: Mapped[str] = mapped_column(
        String(32), nullable=False, default="increase"
    )  # increase | decrease | maintain
    collection_method: Mapped[Optional[str]] = mapped_column(String(128))
    frequency: Mapped[Optional[str]] = mapped_column(String(64))
    baseline_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    baseline_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )  # draft | active | retired
    disaggregation: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    logframe_result: Mapped[Optional[LogframeResult]] = relationship(
        "LogframeResult", back_populates="indicators"
    )
    targets: Mapped[list[IndicatorTarget]] = relationship(
        "IndicatorTarget",
        back_populates="indicator",
        cascade="all, delete-orphan",
        order_by="IndicatorTarget.start_date",
    )
    monitoring_results: Mapped[list[MonitoringResult]] = relationship(
        "MonitoringResult", back_populates="indicator"
    )


class IndicatorTarget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Period target for an indicator."""

    __tablename__ = "indicator_targets"

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
    period_label: Mapped[str] = mapped_column(String(128), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    target_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="planned", index=True
    )  # planned | active | achieved | missed | cancelled
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    indicator: Mapped[Indicator] = relationship("Indicator", back_populates="targets")
    monitoring_results: Mapped[list[MonitoringResult]] = relationship(
        "MonitoringResult", back_populates="target"
    )
