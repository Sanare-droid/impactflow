from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError
from app.db.base import utcnow
from app.models.beneficiary import Beneficiary
from app.models.community import Community
from app.models.field_device import (
    FieldDevice,
    SyncConflictLog,
    SyncMutationLog,
    SyncSession,
)
from app.models.household import Household
from app.models.notification import Notification
from app.models.survey import Survey, SurveyResponse, SurveyVersion
from app.models.task import Task
from app.services import beneficiaries as ben_service
from app.services import devices as device_service
from app.services import notifications as notification_service
from app.services import programs as program_service
from app.services import surveys as survey_service
from app.services.audit import write_audit_log

ENTITY_ORDER = ("community", "household", "beneficiary", "survey_response", "task", "notification")


def _serialize_community(c: Community) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "organization_id": str(c.organization_id),
        "name": c.name,
        "code": c.code,
        "community_type": c.community_type,
        "status": c.status,
        "latitude": str(c.latitude) if c.latitude is not None else None,
        "longitude": str(c.longitude) if c.longitude is not None else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _serialize_household(h: Household) -> dict[str, Any]:
    return {
        "id": str(h.id),
        "organization_id": str(h.organization_id),
        "community_id": str(h.community_id) if h.community_id else None,
        "name": h.name,
        "code": h.code,
        "status": h.status,
        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
    }


def _serialize_beneficiary(b: Beneficiary) -> dict[str, Any]:
    return {
        "id": str(b.id),
        "organization_id": str(b.organization_id),
        "household_id": str(b.household_id) if b.household_id else None,
        "community_id": str(b.community_id) if b.community_id else None,
        "code": b.code,
        "first_name": b.first_name,
        "last_name": b.last_name,
        "middle_name": b.middle_name,
        "phone": b.phone,
        "email": b.email,
        "status": b.status,
        "consent_data_use": b.consent_data_use,
        "latitude": str(b.latitude) if b.latitude is not None else None,
        "longitude": str(b.longitude) if b.longitude is not None else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


def _serialize_survey(s: Survey, version: Optional[SurveyVersion] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(s.id),
        "organization_id": str(s.organization_id),
        "name": s.name,
        "code": s.code,
        "description": s.description,
        "category": s.category,
        "status": s.status,
        "current_version": s.current_version,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
    if version:
        payload["version"] = {
            "id": str(version.id),
            "survey_id": str(version.survey_id),
            "version": version.version,
            "title": version.title,
            "schema": version.schema_,
            "published_at": version.published_at.isoformat() if version.published_at else None,
        }
    return payload


def _serialize_task(t: Task) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "organization_id": str(t.organization_id),
        "project_id": str(t.project_id),
        "activity_id": str(t.activity_id) if t.activity_id else None,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "assignee_id": str(t.assignee_id) if t.assignee_id else None,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _serialize_notification(n: Notification) -> dict[str, Any]:
    return {
        "id": str(n.id),
        "organization_id": str(n.organization_id),
        "user_id": str(n.user_id),
        "event_type": n.event_type,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "severity": n.severity,
        "status": n.status,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


async def _get_mutation_log(
    db: AsyncSession, organization_id: UUID, client_mutation_id: str
) -> Optional[SyncMutationLog]:
    return await db.scalar(
        select(SyncMutationLog).where(
            SyncMutationLog.organization_id == organization_id,
            SyncMutationLog.client_mutation_id == client_mutation_id,
        )
    )


async def _record_mutation(
    db: AsyncSession,
    *,
    organization_id: UUID,
    device_id: Optional[UUID],
    client_mutation_id: str,
    entity_type: str,
    op: str,
    local_id: Optional[str],
    server_id: Optional[UUID],
    status: str,
    error_message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> SyncMutationLog:
    row = SyncMutationLog(
        organization_id=organization_id,
        device_id=device_id,
        client_mutation_id=client_mutation_id,
        entity_type=entity_type,
        op=op,
        local_id=local_id,
        server_id=server_id,
        status=status,
        error_message=error_message,
        payload_json=payload or {},
    )
    db.add(row)
    await db.flush()
    return row


async def start_sync_session(
    db: AsyncSession,
    *,
    organization_id: UUID,
    device_id: UUID,
    user_id: UUID,
    client_version: Optional[str] = None,
) -> SyncSession:
    device = await device_service.get_device(db, organization_id, device_id)
    if device.status != "active":
        raise ConflictError("Device is not active")
    session = SyncSession(
        organization_id=organization_id,
        device_id=device_id,
        user_id=user_id,
        status="running",
        started_at=utcnow(),
        sync_token=utcnow().isoformat(),
        client_version=client_version,
    )
    db.add(session)
    await db.flush()
    return session


async def complete_sync_session(
    db: AsyncSession,
    *,
    session: SyncSession,
    status: str,
    pushed_count: int,
    pulled_count: int,
    failed_count: int,
    error_message: Optional[str] = None,
) -> SyncSession:
    session.status = status
    session.pushed_count = pushed_count
    session.pulled_count = pulled_count
    session.failed_count = failed_count
    session.error_message = error_message
    session.completed_at = utcnow()
    session.sync_token = utcnow().isoformat()
    await db.flush()
    return session


async def _apply_mutation(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    actor_email: str,
    device_id: Optional[UUID],
    entity_type: str,
    op: str,
    payload: dict[str, Any],
    local_id: Optional[str],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[str, Optional[UUID], dict[str, Any]]:
    if entity_type == "community" and op == "create":
        created = await ben_service.create_community(
            db,
            organization_id=organization_id,
            actor_id=user_id,
            actor_email=actor_email,
            data=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return str(created.id), created.id, _serialize_community(created)

    if entity_type == "household" and op == "create":
        created = await ben_service.create_household(
            db,
            organization_id=organization_id,
            actor_id=user_id,
            actor_email=actor_email,
            data=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return str(created.id), created.id, _serialize_household(created)

    if entity_type == "beneficiary" and op == "create":
        created = await ben_service.create_beneficiary(
            db,
            organization_id=organization_id,
            actor_id=user_id,
            actor_email=actor_email,
            data=dict(payload),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return str(created.id), created.id, _serialize_beneficiary(created)

    if entity_type == "beneficiary" and op == "update":
        server_id = payload.pop("server_id", None) or payload.pop("id", None)
        if not server_id:
            raise AppError("server_id required for beneficiary update", code="VALIDATION_ERROR")
        beneficiary = await ben_service.get_beneficiary(
            db, organization_id, UUID(str(server_id))
        )
        updated = await ben_service.update_beneficiary(
            db,
            beneficiary,
            actor_id=user_id,
            actor_email=actor_email,
            data=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return str(updated.id), updated.id, _serialize_beneficiary(updated)

    if entity_type == "survey_response" and op == "create":
        survey_id = payload.get("survey_id")
        if not survey_id:
            raise AppError("survey_id required", code="VALIDATION_ERROR")
        created = await survey_service.submit_response(
            db,
            organization_id=organization_id,
            actor_id=user_id,
            actor_email=actor_email,
            survey_id=UUID(str(survey_id)),
            data=dict(payload),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return str(created.id), created.id, {
            "id": str(created.id),
            "survey_id": str(created.survey_id),
            "status": created.status,
            "updated_at": created.updated_at.isoformat() if created.updated_at else None,
        }

    if entity_type == "task" and op == "update":
        server_id = payload.pop("server_id", None) or payload.pop("id", None)
        if not server_id:
            raise AppError("server_id required for task update", code="VALIDATION_ERROR")
        task = await program_service.get_task(db, organization_id, UUID(str(server_id)))
        updated = await program_service.update_task(
            db,
            task,
            actor_id=user_id,
            actor_email=actor_email,
            data=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return str(updated.id), updated.id, _serialize_task(updated)

    if entity_type == "notification" and op == "update":
        server_id = payload.pop("server_id", None) or payload.pop("id", None)
        if not server_id:
            raise AppError("server_id required", code="VALIDATION_ERROR")
        note = await notification_service.mark_read(
            db,
            organization_id=organization_id,
            user_id=user_id,
            notification_id=UUID(str(server_id)),
        )
        return str(note.id), note.id, _serialize_notification(note)

    raise AppError(f"Unsupported mutation {entity_type}:{op}", code="UNSUPPORTED_MUTATION")


async def batch_push(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    actor_email: str,
    device_id: Optional[UUID],
    mutations: list[dict[str, Any]],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    applied = 0
    failed = 0

    sorted_mutations = sorted(
        mutations,
        key=lambda m: (
            ENTITY_ORDER.index(m.get("entity_type", ""))
            if m.get("entity_type") in ENTITY_ORDER
            else 99,
            m.get("created_at") or "",
        ),
    )

    for item in sorted_mutations:
        client_mutation_id = (item.get("client_mutation_id") or "").strip()
        entity_type = item.get("entity_type") or ""
        op = item.get("op") or ""
        local_id = item.get("local_id")
        payload = item.get("payload") or {}

        if not client_mutation_id:
            results.append(
                {
                    "client_mutation_id": None,
                    "status": "failed",
                    "error": "client_mutation_id required",
                }
            )
            failed += 1
            continue

        existing = await _get_mutation_log(db, organization_id, client_mutation_id)
        if existing and existing.status in ("applied", "duplicate"):
            results.append(
                {
                    "client_mutation_id": client_mutation_id,
                    "status": "duplicate",
                    "server_id": str(existing.server_id) if existing.server_id else None,
                    "entity_type": existing.entity_type,
                }
            )
            applied += 1
            continue

        try:
            server_id_str, server_uuid, record = await _apply_mutation(
                db,
                organization_id=organization_id,
                user_id=user_id,
                actor_email=actor_email,
                device_id=device_id,
                entity_type=entity_type,
                op=op,
                payload=dict(payload),
                local_id=local_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await _record_mutation(
                db,
                organization_id=organization_id,
                device_id=device_id,
                client_mutation_id=client_mutation_id,
                entity_type=entity_type,
                op=op,
                local_id=local_id,
                server_id=server_uuid,
                status="applied",
                payload=payload,
            )
            results.append(
                {
                    "client_mutation_id": client_mutation_id,
                    "status": "applied",
                    "server_id": server_id_str,
                    "local_id": local_id,
                    "entity_type": entity_type,
                    "record": record,
                }
            )
            applied += 1
        except Exception as exc:
            message = str(exc)
            await _record_mutation(
                db,
                organization_id=organization_id,
                device_id=device_id,
                client_mutation_id=client_mutation_id,
                entity_type=entity_type,
                op=op,
                local_id=local_id,
                server_id=None,
                status="failed",
                error_message=message,
                payload=payload,
            )
            results.append(
                {
                    "client_mutation_id": client_mutation_id,
                    "status": "failed",
                    "error": message,
                    "local_id": local_id,
                    "entity_type": entity_type,
                }
            )
            failed += 1

    if device_id:
        device = await device_service.get_device(db, organization_id, device_id)
        device.last_sync_at = utcnow()
        await db.flush()

    return {"results": results, "applied": applied, "failed": failed}


async def delta_pull(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    since: Optional[datetime] = None,
    entities: Optional[list[str]] = None,
    page_size: int = 100,
) -> dict[str, Any]:
    want = set(entities or ["communities", "households", "beneficiaries", "surveys", "tasks", "notifications"])
    server_time = utcnow()
    payload: dict[str, Any] = {"server_time": server_time.isoformat(), "since": since.isoformat() if since else None}

    if "communities" in want:
        items, _ = await ben_service.list_communities(
            db, organization_id, page=1, page_size=page_size, updated_after=since
        )
        payload["communities"] = [_serialize_community(c) for c in items]

    if "households" in want:
        items, _ = await ben_service.list_households(
            db, organization_id, page=1, page_size=page_size, updated_after=since
        )
        payload["households"] = [_serialize_household(h) for h in items]

    if "beneficiaries" in want:
        items, _ = await ben_service.list_beneficiaries(
            db, organization_id, page=1, page_size=page_size, updated_after=since
        )
        payload["beneficiaries"] = [_serialize_beneficiary(b) for b in items]

    if "surveys" in want:
        surveys, _ = await survey_service.list_surveys(
            db, organization_id, page=1, page_size=page_size, status="published", updated_after=since
        )
        survey_payloads = []
        for s in surveys:
            try:
                version = await survey_service.get_current_version(db, s)
                survey_payloads.append(_serialize_survey(s, version))
            except Exception:
                survey_payloads.append(_serialize_survey(s))
        payload["surveys"] = survey_payloads

    if "tasks" in want:
        items, _ = await program_service.list_tasks(
            db,
            organization_id,
            page=1,
            page_size=page_size,
            assignee_id=user_id,
            updated_after=since,
        )
        payload["tasks"] = [_serialize_task(t) for t in items]

    if "notifications" in want:
        items, _ = await notification_service.list_notifications(
            db,
            organization_id=organization_id,
            user_id=user_id,
            page=1,
            page_size=page_size,
            updated_after=since,
        )
        payload["notifications"] = [_serialize_notification(n) for n in items]

    payload["sync_token"] = server_time.isoformat()
    return payload


async def list_sync_sessions(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    device_id: Optional[UUID] = None,
) -> tuple[list[SyncSession], int]:
    filters = [SyncSession.organization_id == organization_id]
    if device_id:
        filters.append(SyncSession.device_id == device_id)
    total = await db.scalar(select(func.count()).select_from(SyncSession).where(*filters)) or 0
    rows = await db.scalars(
        select(SyncSession)
        .where(*filters)
        .order_by(SyncSession.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def log_conflict(
    db: AsyncSession,
    *,
    organization_id: UUID,
    device_id: Optional[UUID],
    user_id: Optional[UUID],
    entity_type: str,
    local_id: Optional[str],
    server_id: Optional[UUID],
    local_snapshot: dict,
    server_snapshot: dict,
) -> SyncConflictLog:
    row = SyncConflictLog(
        organization_id=organization_id,
        device_id=device_id,
        user_id=user_id,
        entity_type=entity_type,
        local_id=local_id,
        server_id=server_id,
        resolution="server_wins",
        local_snapshot=local_snapshot,
        server_snapshot=server_snapshot,
    )
    db.add(row)
    await db.flush()
    return row


async def field_ops_metrics(
    db: AsyncSession, organization_id: UUID
) -> dict[str, int]:
    devices_active = (
        await db.scalar(
            select(func.count())
            .select_from(FieldDevice)
            .where(FieldDevice.organization_id == organization_id, FieldDevice.status == "active")
        )
        or 0
    )
    pending_media = (
        await db.scalar(
            select(func.count())
            .select_from(SyncMutationLog)
            .where(
                SyncMutationLog.organization_id == organization_id,
                SyncMutationLog.status == "failed",
            )
        )
        or 0
    )
    recent_syncs = (
        await db.scalar(
            select(func.count())
            .select_from(SyncSession)
            .where(SyncSession.organization_id == organization_id)
        )
        or 0
    )
    conflicts = (
        await db.scalar(
            select(func.count())
            .select_from(SyncConflictLog)
            .where(SyncConflictLog.organization_id == organization_id)
        )
        or 0
    )
    return {
        "active_devices": devices_active,
        "failed_mutations": pending_media,
        "sync_sessions": recent_syncs,
        "conflicts": conflicts,
    }
