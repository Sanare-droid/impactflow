from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str | UUID] = None,
    organization_id: Optional[UUID] = None,
    actor_id: Optional[UUID] = None,
    actor_email: Optional[str] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    changes: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
    status: str = "success",
) -> AuditLog:
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        changes=changes or {},
        metadata_=metadata or {},
        status=status,
    )
    db.add(entry)
    await db.flush()
    return entry
