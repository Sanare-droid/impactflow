from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.user import User
from app.services.auth import get_user_permissions

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class RequestContext:
    user: User
    organization: Optional[Organization] = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    membership: Optional[OrganizationMembership] = None

    def has_permission(self, code: str) -> bool:
        if self.user.is_platform_admin or self.user.is_superuser:
            return True
        if "organizations:manage" in self.permissions:
            return True
        return code in self.permissions

    def require_permission(self, *codes: str) -> None:
        if not any(self.has_permission(code) for code in codes):
            raise ForbiddenError(
                "Insufficient permissions",
                details={"required": list(codes)},
            )


async def get_current_context(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    x_organization_id: Annotated[Optional[str], Header(alias="X-Organization-Id")] = None,
) -> RequestContext:
    if not credentials:
        raise UnauthorizedError("Authentication required")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token subject")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    org_id_raw = x_organization_id or payload.get("org_id")
    organization: Optional[Organization] = None
    roles: list[str] = list(payload.get("roles") or [])
    permissions: list[str] = list(payload.get("permissions") or [])
    membership: Optional[OrganizationMembership] = None

    if org_id_raw:
        org_id = UUID(str(org_id_raw))
        organization = await db.get(Organization, org_id)
        if not organization or not organization.is_active:
            raise ForbiddenError("Organization unavailable")
        # Always resolve live permissions from DB for accuracy
        permissions, role, membership = await get_user_permissions(db, user.id, org_id)
        if not membership and not (user.is_superuser or user.is_platform_admin):
            raise ForbiddenError("Not a member of this organization")
        roles = [role.slug] if role else roles

    request.state.user_id = str(user.id)
    request.state.organization_id = str(organization.id) if organization else None

    return RequestContext(
        user=user,
        organization=organization,
        roles=roles,
        permissions=permissions,
        membership=membership,
    )


def require_permissions(*codes: str):
    async def _dependency(
        ctx: Annotated[RequestContext, Depends(get_current_context)],
    ) -> RequestContext:
        ctx.require_permission(*codes)
        return ctx

    return _dependency


def client_meta(request: Request) -> tuple[Optional[str], Optional[str]]:
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("user-agent")
    return ip, ua
