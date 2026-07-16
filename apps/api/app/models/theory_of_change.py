from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.logframe import Logframe


class TheoryOfChange(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Causal pathway linking problem → interventions → outcomes → impact."""

    __tablename__ = "theories_of_change"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_theories_of_change_org_code"),
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )  # draft | active | archived
    goal_statement: Mapped[Optional[str]] = mapped_column(Text)
    problem_statement: Mapped[Optional[str]] = mapped_column(Text)
    assumptions: Mapped[Optional[str]] = mapped_column(Text)
    success_criteria: Mapped[Optional[str]] = mapped_column(Text)
    pathways: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    logframes: Mapped[list[Logframe]] = relationship(
        "Logframe", back_populates="theory_of_change"
    )
