from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class AiPrediction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stored risk / outcome prediction for a program or project."""

    __tablename__ = "ai_predictions"

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
    prediction_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="project_risk", index=True
    )  # project_risk | delivery_delay | data_quality | budget_burn | custom
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(32), nullable=False, default="medium", index=True
    )  # low | medium | high | critical
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("50"))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open", index=True
    )  # open | acknowledged | resolved | dismissed
    recommendations: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    signals: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="fallback")
    model: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
