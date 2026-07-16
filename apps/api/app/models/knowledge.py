from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class KnowledgeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Knowledge base article for RAG / organizational memory."""

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_knowledge_documents_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="guidance", index=True
    )  # guidance | sop | lessons | policy | faq | other
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="published", index=True
    )  # draft | published | archived
    summary: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(255))
    tags: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    # Placeholder for future vector embeddings / chunk refs
    embedding_ref: Mapped[Optional[str]] = mapped_column(String(255))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
