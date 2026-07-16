from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.indicator import Indicator
    from app.models.theory_of_change import TheoryOfChange


class Logframe(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logical framework / results framework for a program or project."""

    __tablename__ = "logframes"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_logframes_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    theory_of_change_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("theories_of_change.id", ondelete="SET NULL"),
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
        String(32), nullable=False, default="draft", index=True
    )  # draft | active | archived
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    theory_of_change: Mapped[Optional[TheoryOfChange]] = relationship(
        "TheoryOfChange", back_populates="logframes"
    )
    results: Mapped[list[LogframeResult]] = relationship(
        "LogframeResult",
        back_populates="logframe",
        cascade="all, delete-orphan",
        order_by="LogframeResult.sort_order",
    )


class LogframeResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Impact / outcome / output / activity row within a logframe."""

    __tablename__ = "logframe_results"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    logframe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("logframes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("logframe_results.id", ondelete="SET NULL"),
        index=True,
    )
    level: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # impact | outcome | output | activity
    code: Mapped[Optional[str]] = mapped_column(String(64))
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[Optional[str]] = mapped_column(Text)
    means_of_verification: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    logframe: Mapped[Logframe] = relationship("Logframe", back_populates="results")
    indicators: Mapped[list[Indicator]] = relationship(
        "Indicator", back_populates="logframe_result"
    )
