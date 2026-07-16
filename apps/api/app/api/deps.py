from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import PERMISSION_CATALOG
from app.core.security import decode_token, verify_password
from app.db.base import utcnow
from app.db.session import get_db
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.platform import OrgApiKey
from app.models.user import User
from app.services.auth import get_user_permissions

bearer_scheme = HTTPBearer(auto_error=False)

_ALL_READ = [
    p["code"]
    for p in PERMISSION_CATALOG
    if p["action"] in ("read", "use", "export")
]
_ALL_WRITE = [
    p["code"]
    for p in PERMISSION_CATALOG
    if p["action"] in ("manage", "create", "update", "delete", "approve", "submit")
]


@dataclass
class RequestContext:
    user: User
    organization: Optional[Organization] = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    membership: Optional[OrganizationMembership] = None
    auth_method: str = "jwt"  # jwt | api_key
    api_key_id: Optional[UUID] = None

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


def _expand_api_key_scopes(scopes: list) -> list[str]:
    expanded: set[str] = set()
    for scope in scopes or []:
        s = str(scope).strip()
        if s in ("*", "all"):
            expanded.update(p["code"] for p in PERMISSION_CATALOG)
        elif s == "read":
            expanded.update(_ALL_READ)
        elif s in ("write", "manage"):
            expanded.update(_ALL_WRITE)
            expanded.update(_ALL_READ)
        elif ":" in s:
            expanded.add(s)
    return sorted(expanded)


def _service_user_stub(*, organization_id: UUID, key_name: str) -> User:
    """Synthetic user object for API-key auth (not persisted)."""
    user = User(
        email=f"apikey+{organization_id}@impactflow.local",
        hashed_password="!",
        first_name="API",
        last_name="Key",
        display_name=key_name,
        is_active=True,
        primary_organization_id=organization_id,
    )
    # Ensure id exists for audit contexts
    from uuid import uuid4

    user.id = uuid4()
    return user


async def _authenticate_api_key(
    db: AsyncSession,
    *,
    raw_key: str,
    x_organization_id: Optional[str],
) -> RequestContext:
    if not raw_key.startswith("if_"):
        raise UnauthorizedError("Invalid API key")
    prefix = raw_key[:10]
    candidates = await db.scalars(
        select(OrgApiKey).where(
            OrgApiKey.key_prefix == prefix,
            OrgApiKey.status == "active",
        )
    )
    matched: Optional[OrgApiKey] = None
    for key in candidates:
        if verify_password(raw_key, key.key_hash):
            matched = key
            break
    if not matched:
        raise UnauthorizedError("Invalid API key")
    if matched.expires_at and matched.expires_at < utcnow():
        raise UnauthorizedError("API key expired")

    organization = await db.get(Organization, matched.organization_id)
    if not organization or not organization.is_active:
        raise ForbiddenError("Organization unavailable")

    if x_organization_id and str(organization.id) != str(x_organization_id):
        raise ForbiddenError("API key organization mismatch")

    matched.last_used_at = utcnow()
    await db.flush()

    permissions = _expand_api_key_scopes(list(matched.scopes or []))
    user = _service_user_stub(organization_id=organization.id, key_name=matched.name)
    return RequestContext(
        user=user,
        organization=organization,
        roles=["api_key"],
        permissions=permissions,
        membership=None,
        auth_method="api_key",
        api_key_id=matched.id,
    )


async def get_current_context(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
    x_organization_id: Annotated[Optional[str], Header(alias="X-Organization-Id")] = None,
    x_api_key: Annotated[Optional[str], Header(alias="X-Api-Key")] = None,
) -> RequestContext:
    # Prefer explicit API key header, else Bearer if_… key, else JWT
    raw_api_key = x_api_key
    if (
        not raw_api_key
        and credentials
        and credentials.credentials
        and credentials.credentials.startswith("if_")
    ):
        raw_api_key = credentials.credentials

    if raw_api_key:
        ctx = await _authenticate_api_key(
            db, raw_key=raw_api_key, x_organization_id=x_organization_id
        )
        request.state.user_id = str(ctx.user.id)
        request.state.organization_id = str(ctx.organization.id) if ctx.organization else None
        request.state.auth_method = "api_key"
        return ctx

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
        permissions, role, membership = await get_user_permissions(db, user.id, org_id)
        if not membership and not (user.is_superuser or user.is_platform_admin):
            raise ForbiddenError("Not a member of this organization")
        roles = [role.slug] if role else roles

    request.state.user_id = str(user.id)
    request.state.organization_id = str(organization.id) if organization else None
    request.state.auth_method = "jwt"

    return RequestContext(
        user=user,
        organization=organization,
        roles=roles,
        permissions=permissions,
        membership=membership,
        auth_method="jwt",
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
