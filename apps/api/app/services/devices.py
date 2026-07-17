from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.base import utcnow
from app.models.field_device import FieldDevice, MediaUploadRecord
from app.services.audit import write_audit_log


async def get_device(
    db: AsyncSession, organization_id: UUID, device_id: UUID
) -> FieldDevice:
    row = await db.scalar(
        select(FieldDevice).where(
            FieldDevice.id == device_id,
            FieldDevice.organization_id == organization_id,
        )
    )
    if not row:
        raise NotFoundError("Device not found")
    return row


async def register_device(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    actor_email: str,
    device_key: str,
    name: str,
    platform: str,
    app_version: Optional[str],
    push_token: Optional[str] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> FieldDevice:
    key = device_key.strip()
    if not key:
        raise ConflictError("device_key is required")

    existing = await db.scalar(
        select(FieldDevice).where(
            FieldDevice.organization_id == organization_id,
            FieldDevice.device_key == key,
        )
    )
    now = utcnow()
    if existing:
        if existing.status == "revoked":
            raise ConflictError("Device has been revoked — contact your administrator")
        existing.user_id = user_id
        existing.name = name.strip() or existing.name
        existing.platform = platform or existing.platform
        existing.app_version = app_version or existing.app_version
        existing.push_token = push_token or existing.push_token
        existing.last_seen_at = now
        existing.status = "active"
        if metadata:
            existing.metadata_ = {**existing.metadata_, **metadata}
        await db.flush()
        device = existing
    else:
        device = FieldDevice(
            organization_id=organization_id,
            user_id=user_id,
            device_key=key,
            name=name.strip() or "Field Device",
            platform=platform or "unknown",
            app_version=app_version,
            push_token=push_token,
            last_seen_at=now,
            metadata_=metadata or {},
        )
        db.add(device)
        await db.flush()
        await write_audit_log(
            db,
            action="devices.register",
            resource_type="field_device",
            resource_id=device.id,
            organization_id=organization_id,
            actor_id=user_id,
            actor_email=actor_email,
            description=f"Registered field device {device.name}",
            changes={"device_key": key, "platform": platform},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    return device


async def heartbeat_device(
    db: AsyncSession,
    *,
    organization_id: UUID,
    device_id: UUID,
    app_version: Optional[str] = None,
    storage_bytes: Optional[int] = None,
    pending_uploads: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> FieldDevice:
    device = await get_device(db, organization_id, device_id)
    if device.status != "active":
        raise ConflictError("Device is not active")
    device.last_seen_at = utcnow()
    if app_version:
        device.app_version = app_version
    if storage_bytes is not None:
        device.storage_bytes = max(0, storage_bytes)
    if pending_uploads is not None:
        device.pending_uploads = max(0, pending_uploads)
    if metadata:
        device.metadata_ = {**device.metadata_, **metadata}
    await db.flush()
    return device


async def list_devices(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    user_id: Optional[UUID] = None,
) -> tuple[list[FieldDevice], int]:
    filters = [FieldDevice.organization_id == organization_id]
    if status:
        filters.append(FieldDevice.status == status)
    if user_id:
        filters.append(FieldDevice.user_id == user_id)
    total = await db.scalar(select(func.count()).select_from(FieldDevice).where(*filters)) or 0
    rows = await db.scalars(
        select(FieldDevice)
        .where(*filters)
        .order_by(FieldDevice.last_seen_at.desc().nullslast(), FieldDevice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def update_device_status(
    db: AsyncSession,
    *,
    organization_id: UUID,
    device_id: UUID,
    status: str,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> FieldDevice:
    device = await get_device(db, organization_id, device_id)
    if status not in ("active", "deactivated", "revoked"):
        raise ConflictError("Invalid device status")
    device.status = status
    await db.flush()
    await write_audit_log(
        db,
        action="devices.update_status",
        resource_type="field_device",
        resource_id=device.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Device {device.name} set to {status}",
        changes={"status": status},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return device


async def list_media_uploads(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    device_id: Optional[UUID] = None,
) -> tuple[list[MediaUploadRecord], int]:
    filters = [MediaUploadRecord.organization_id == organization_id]
    if status:
        filters.append(MediaUploadRecord.status == status)
    if device_id:
        filters.append(MediaUploadRecord.device_id == device_id)
    total = (
        await db.scalar(select(func.count()).select_from(MediaUploadRecord).where(*filters)) or 0
    )
    rows = await db.scalars(
        select(MediaUploadRecord)
        .where(*filters)
        .order_by(MediaUploadRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def register_media_upload(
    db: AsyncSession,
    *,
    organization_id: UUID,
    device_id: Optional[UUID],
    client_mutation_id: str,
    entity_type: str,
    entity_id: Optional[UUID],
    file_name: str,
    mime_type: Optional[str],
    file_size: int,
    metadata: Optional[dict] = None,
) -> MediaUploadRecord:
    existing = await db.scalar(
        select(MediaUploadRecord).where(
            MediaUploadRecord.organization_id == organization_id,
            MediaUploadRecord.client_mutation_id == client_mutation_id,
        )
    )
    if existing:
        return existing
    row = MediaUploadRecord(
        organization_id=organization_id,
        device_id=device_id,
        client_mutation_id=client_mutation_id,
        entity_type=entity_type,
        entity_id=entity_id,
        file_name=file_name,
        mime_type=mime_type,
        file_size=file_size,
        status="pending",
        metadata_=metadata or {},
    )
    db.add(row)
    await db.flush()
    return row


async def complete_media_upload(
    db: AsyncSession,
    *,
    organization_id: UUID,
    upload_id: UUID,
    remote_url: str,
    file_size: Optional[int] = None,
    mime_type: Optional[str] = None,
    error_message: Optional[str] = None,
) -> MediaUploadRecord:
    row = await db.scalar(
        select(MediaUploadRecord).where(
            MediaUploadRecord.organization_id == organization_id,
            MediaUploadRecord.id == upload_id,
        )
    )
    if not row:
        raise NotFoundError("Media upload not found")
    if error_message:
        row.status = "failed"
        row.error_message = error_message
    else:
        row.status = "uploaded"
        row.remote_url = remote_url
        row.error_message = None
        if file_size is not None:
            row.file_size = file_size
        if mime_type:
            row.mime_type = mime_type
    await db.flush()
    return row
