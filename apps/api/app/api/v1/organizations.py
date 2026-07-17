from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import RequestContext, client_meta, get_current_context, require_permissions
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.db.session import get_db
from app.models.membership import OrganizationMembership
from app.models.permission import Permission, RolePermission
from app.models.role import Role
from app.schemas import (
    InviteUserRequest,
    MembershipResponse,
    OrganizationResponse,
    OrganizationUpdateRequest,
    PaginatedResponse,
    PaginationMeta,
    PermissionResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    UpdateMembershipRoleRequest,
    UserBrief,
    UserResponse,
    UserUpdateRequest,
)
from app.services import auth as auth_service
from app.services.audit import write_audit_log

router = APIRouter(tags=["Organizations & Users"])


@router.get("/organizations/current", response_model=OrganizationResponse)
async def get_current_organization(
    ctx: Annotated[RequestContext, Depends(require_permissions("organizations:read"))],
) -> OrganizationResponse:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    return OrganizationResponse.model_validate(ctx.organization)


@router.patch("/organizations/current", response_model=OrganizationResponse)
async def update_current_organization(
    body: OrganizationUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("organizations:update", "organizations:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationResponse:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    org = ctx.organization
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(org, key, value)
    ip, ua = client_meta(request)
    await write_audit_log(
        db,
        action="organizations.update",
        resource_type="organization",
        resource_id=org.id,
        organization_id=org.id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        description="Organization profile updated",
        changes=data,
        ip_address=ip,
        user_agent=ua,
    )
    await db.flush()
    return OrganizationResponse.model_validate(org)


@router.get("/users/me", response_model=UserResponse)
async def get_me(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
) -> UserResponse:
    return UserResponse.model_validate(ctx.user)


@router.patch("/users/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(ctx.user, key, value)
    await db.flush()
    return UserResponse.model_validate(ctx.user)


@router.get("/users", response_model=PaginatedResponse[MembershipResponse])
async def list_users(
    ctx: Annotated[RequestContext, Depends(require_permissions("users:read", "users:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[MembershipResponse]:
    if not ctx.organization:
        raise NotFoundError("No active organization context")

    base = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == ctx.organization.id
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(
        base.options(
            selectinload(OrganizationMembership.user),
            selectinload(OrganizationMembership.role).selectinload(
                Role.role_permissions
            ).selectinload(RolePermission.permission),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .order_by(OrganizationMembership.created_at.desc())
    )
    items = []
    for m in result.scalars().all():
        role_perms = [rp.permission.code for rp in m.role.role_permissions]
        items.append(
            MembershipResponse(
                id=m.id,
                organization_id=m.organization_id,
                user_id=m.user_id,
                role_id=m.role_id,
                status=m.status,
                user=UserBrief.model_validate(m.user) if m.user else None,
                role=RoleResponse(
                    id=m.role.id,
                    name=m.role.name,
                    slug=m.role.slug,
                    description=m.role.description,
                    is_system=m.role.is_system,
                    is_default=m.role.is_default,
                    organization_id=m.role.organization_id,
                    permissions=role_perms,
                ),
            )
        )
    total = total or 0
    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/users/invite", response_model=dict, status_code=201)
async def invite_user(
    body: InviteUserRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("users:create", "users:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    from app.services import enterprise as ent
    from app.services.rate_limit import enforce_rate_limit

    ip, ua = client_meta(request)
    # Bound concurrent invite storms per org + IP (DB work stays cheap; email is async).
    await enforce_rate_limit(
        key=f"rl:invite:org:{ctx.organization.id}",
        limit=60,
        window_seconds=60,
    )
    await enforce_rate_limit(key=f"rl:invite:ip:{ip or 'unknown'}", limit=30, window_seconds=60)

    await ent.enforce_writable(db, ctx.organization.id)
    await ent.enforce_seat_limit(db, ctx.organization.id)
    user, temp_password, delivery = await auth_service.invite_user(
        db,
        organization_id=ctx.organization.id,
        email=str(body.email),
        first_name=body.first_name,
        last_name=body.last_name,
        role_id=body.role_id,
        actor=ctx.user,
        job_title=body.job_title,
        send_invite=body.send_invite,
        ip_address=ip,
        user_agent=ua,
    )

    status = (delivery or {}).get("status") or "skipped"
    if not body.send_invite:
        message = (
            "User invited. Copy the temporary password and share it securely."
            if temp_password
            else "User invited."
        )
    elif status == "queued":
        if delivery.get("resend_dev_from"):
            message = (
                "User invited. Email is queued, but the server From address is still "
                "Resend's test domain (onboarding@resend.dev), which usually only "
                "delivers to the Resend account owner. Copy the temporary password below "
                "and set SMTP_FROM to a verified domain for real invite emails."
            )
        else:
            message = (
                "User invited. An invite email is being sent in the background. "
                "Copy the temporary password below in case delivery is delayed."
            )
    elif status in {"not_configured", "queued_stub"}:
        message = (
            "User invited. Outbound email is not configured on this server — "
            "copy the temporary password and share it securely."
            if temp_password
            else "User invited. Outbound email is not configured on this server."
        )
    elif status == "failed":
        message = (
            "User invited, but email delivery failed. "
            "Copy the temporary password and share it securely."
            if temp_password
            else "User invited, but email delivery failed."
        )
    elif status == "sent":
        message = (
            "User invited. Temporary password emailed — also shown once below."
            if temp_password
            else "User invited. Invite email sent."
        )
    else:
        message = "User invited."

    payload: dict = {
        "user": UserBrief.model_validate(user),
        "message": message,
        "email_delivery": {
            "status": status,
            "provider": delivery.get("provider"),
            "resend_dev_from": bool(delivery.get("resend_dev_from")),
        },
    }
    # Only return temp password once for newly created users (never log it)
    if temp_password:
        payload["temporary_password"] = temp_password
    return payload


def _membership_response(m: OrganizationMembership) -> MembershipResponse:
    role_perms = [
        rp.permission.code
        for rp in (m.role.role_permissions if m.role else [])
        if rp.permission
    ]
    return MembershipResponse(
        id=m.id,
        organization_id=m.organization_id,
        user_id=m.user_id,
        role_id=m.role_id,
        status=m.status,
        user=UserBrief.model_validate(m.user) if m.user else None,
        role=RoleResponse(
            id=m.role.id,
            name=m.role.name,
            slug=m.role.slug,
            description=m.role.description,
            is_system=m.role.is_system,
            is_default=m.role.is_default,
            organization_id=m.role.organization_id,
            permissions=role_perms,
        )
        if m.role
        else None,
    )


@router.patch(
    "/users/memberships/{membership_id}",
    response_model=MembershipResponse,
)
async def update_membership_role(
    membership_id: UUID,
    body: UpdateMembershipRoleRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("users:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MembershipResponse:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    ip, ua = client_meta(request)
    membership = await auth_service.update_membership_role(
        db,
        organization_id=ctx.organization.id,
        membership_id=membership_id,
        role_id=body.role_id,
        actor=ctx.user,
        ip_address=ip,
        user_agent=ua,
    )
    # Reload with permissions for response
    result = await db.execute(
        select(OrganizationMembership)
        .options(
            selectinload(OrganizationMembership.user),
            selectinload(OrganizationMembership.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission),
        )
        .where(OrganizationMembership.id == membership.id)
    )
    loaded = result.scalar_one()
    return _membership_response(loaded)


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    ctx: Annotated[RequestContext, Depends(require_permissions("roles:read", "roles:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RoleResponse]:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    result = await db.execute(
        select(Role)
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
        .where(Role.organization_id == ctx.organization.id)
        .order_by(Role.name)
    )
    roles = []
    for role in result.scalars().all():
        roles.append(
            RoleResponse(
                id=role.id,
                name=role.name,
                slug=role.slug,
                description=role.description,
                is_system=role.is_system,
                is_default=role.is_default,
                organization_id=role.organization_id,
                permissions=[rp.permission.code for rp in role.role_permissions],
            )
        )
    return roles


def _slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "role"


async def _role_response(db: AsyncSession, role: Role) -> RoleResponse:
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        .where(Role.id == role.id)
    )
    loaded = result.scalar_one()
    return RoleResponse(
        id=loaded.id,
        name=loaded.name,
        slug=loaded.slug,
        description=loaded.description,
        is_system=loaded.is_system,
        is_default=loaded.is_default,
        organization_id=loaded.organization_id,
        permissions=[rp.permission.code for rp in loaded.role_permissions],
    )


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("roles:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleResponse:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    slug = body.slug or _slugify(body.name)
    existing = await db.scalar(
        select(Role).where(
            Role.organization_id == ctx.organization.id,
            Role.slug == slug,
        )
    )
    if existing:
        raise ConflictError("A role with this slug already exists")
    role = Role(
        organization_id=ctx.organization.id,
        name=body.name,
        slug=slug,
        description=body.description,
        is_system=False,
        is_default=body.is_default,
    )
    db.add(role)
    await db.flush()
    if body.permissions:
        perms = await db.scalars(select(Permission).where(Permission.code.in_(body.permissions)))
        for perm in perms:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    ip, ua = client_meta(request)
    await write_audit_log(
        db,
        action="roles.create",
        resource_type="role",
        resource_id=role.id,
        organization_id=ctx.organization.id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        description=f"Created role {role.name}",
        ip_address=ip,
        user_agent=ua,
    )
    await db.flush()
    return await _role_response(db, role)


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    body: RoleUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("roles:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleResponse:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    role = await db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == ctx.organization.id,
        )
    )
    if not role:
        raise NotFoundError("Role not found")
    if role.is_system and body.permissions is not None:
        raise AppError("System role permissions cannot be replaced", code="FORBIDDEN")
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    if body.is_default is not None:
        role.is_default = body.is_default
    if body.permissions is not None and not role.is_system:
        existing = await db.scalars(select(RolePermission).where(RolePermission.role_id == role.id))
        for rp in existing:
            await db.delete(rp)
        perms = await db.scalars(select(Permission).where(Permission.code.in_(body.permissions)))
        for perm in perms:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    ip, ua = client_meta(request)
    await write_audit_log(
        db,
        action="roles.update",
        resource_type="role",
        resource_id=role.id,
        organization_id=ctx.organization.id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        description=f"Updated role {role.name}",
        ip_address=ip,
        user_agent=ua,
    )
    await db.flush()
    return await _role_response(db, role)


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    ctx: Annotated[RequestContext, Depends(require_permissions("roles:read", "roles:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PermissionResponse]:
    from app.models.permission import Permission

    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    return [PermissionResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/me/permissions")
async def my_permissions(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
) -> dict:
    return {
        "roles": ctx.roles,
        "permissions": ctx.permissions,
        "organization_id": str(ctx.organization.id) if ctx.organization else None,
    }
