from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.program import Program
    from app.models.task import Task
    from app.models.work_plan import WorkPlan


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Operational delivery unit under a program."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_projects_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="planning", index=True
    )  # planning | active | on_hold | completed | cancelled | archived
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    tags: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    program: Mapped[Program] = relationship("Program", back_populates="projects")
    activities: Mapped[list[Activity]] = relationship(
        "Activity", back_populates="project", cascade="all, delete-orphan"
    )
    work_plans: Mapped[list[WorkPlan]] = relationship(
        "WorkPlan", back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
