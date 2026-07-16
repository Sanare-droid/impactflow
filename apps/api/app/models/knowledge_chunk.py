"""Knowledge chunk storage for RAG retrieval."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class KnowledgeChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Chunk of a knowledge document with a portable embedding vector."""

    __tablename__ = "knowledge_chunks"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON list[float] — hashing embed by default; OpenAI when configured
    embedding: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False, default="hash-v1")
    token_estimate: Mapped[Optional[int]] = mapped_column(Integer)
