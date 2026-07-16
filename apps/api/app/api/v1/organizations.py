from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import RequestContext, client_meta, get_current_context, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.permission import RolePermission
from app.models.role import Role
from app.models.user import User
from app.schemas import (
    InviteUserRequest,
    MembershipResponse,
    MessageResponse,
    OrganizationResponse,
    OrganizationUpdateRequest,
    PaginatedResponse,
    PaginationMeta,
    PermissionResponse,
    RoleResponse,
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
    user, temp_password = await auth_service.invite_user(
        db,
        organization_id=ctx.organization.id,
        email=str(body.email),
        first_name=body.first_name,
        last_name=body.last_name,
        role_id=body.role_id,
        actor=ctx.user,
        job_title=body.job_title,
    )
    # Temporary password returned once — in production send via email provider
    return {
        "user": UserBrief.model_validate(user),
        "temporary_password": temp_password,
        "message": "User invited. Deliver the temporary password securely.",
    }


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
