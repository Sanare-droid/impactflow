from __future__ import annotations

import re
import secrets
import string
from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.permissions import PERMISSION_CATALOG, SYSTEM_ROLES
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_secret,
    encrypt_secret,
    generate_mfa_secret,
    hash_password,
    hash_token,
    mfa_provisioning_uri,
    verify_mfa_code,
    verify_password,
)
from app.db.base import utcnow
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.permission import Permission, RolePermission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.services.audit import write_audit_log


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:100] or secrets.token_hex(4)


def generate_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def ensure_permission_catalog(db: AsyncSession) -> dict[str, Permission]:
    result = await db.execute(select(Permission))
    existing = {p.code: p for p in result.scalars().all()}
    for item in PERMISSION_CATALOG:
        if item["code"] not in existing:
            perm = Permission(**item)
            db.add(perm)
            existing[item["code"]] = perm
    await db.flush()
    return existing


async def create_org_system_roles(
    db: AsyncSession,
    organization_id: UUID,
    permissions_by_code: dict[str, Permission],
) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for slug, meta in SYSTEM_ROLES.items():
        role = Role(
            organization_id=organization_id,
            name=meta["name"],
            slug=slug,
            description=meta["description"],
            is_system=True,
            is_default=bool(meta.get("is_default", False)),
        )
        db.add(role)
        await db.flush()
        for code in meta["permissions"]:
            perm = permissions_by_code.get(code)
            if perm:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        roles[slug] = role
    await db.flush()
    return roles


async def sync_system_role_permissions(db: AsyncSession) -> None:
    """Ensure catalog + system roles reflect current PERMISSION_CATALOG / SYSTEM_ROLES."""
    permissions_by_code = await ensure_permission_catalog(db)
    roles = (
        await db.execute(select(Role).where(Role.is_system.is_(True)))
    ).scalars().all()
    for role in roles:
        meta = SYSTEM_ROLES.get(role.slug)
        if not meta:
            continue
        existing = {
            rp.permission_id
            for rp in (
                await db.execute(
                    select(RolePermission).where(RolePermission.role_id == role.id)
                )
            ).scalars().all()
        }
        # Also load by permission code via join for clarity
        existing_codes = set(
            (
                await db.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == role.id)
                )
            ).scalars().all()
        )
        for code in meta["permissions"]:
            if code in existing_codes:
                continue
            perm = permissions_by_code.get(code)
            if perm and perm.id not in existing:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    await db.flush()


async def get_user_permissions(
    db: AsyncSession, user_id: UUID, organization_id: UUID
) -> tuple[list[str], Optional[Role], Optional[OrganizationMembership]]:
    result = await db.execute(
        select(OrganizationMembership)
        .options(
            selectinload(OrganizationMembership.role).selectinload(
                Role.role_permissions
            ).selectinload(RolePermission.permission)
        )
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == "active",
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return [], None, None
    codes = [
        rp.permission.code
        for rp in membership.role.role_permissions
        if rp.permission
    ]
    return sorted(set(codes)), membership.role, membership


async def register_organization(
    db: AsyncSession,
    *,
    organization_name: str,
    organization_slug: Optional[str],
    organization_type: str,
    country_code: Optional[str],
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[Organization, User, str, str]:
    email_norm = email.lower().strip()
    existing = await db.execute(select(User).where(User.email == email_norm))
    if existing.scalar_one_or_none():
        raise ConflictError("A user with this email already exists")

    slug = slugify(organization_slug or organization_name)
    slug_exists = await db.execute(select(Organization).where(Organization.slug == slug))
    if slug_exists.scalar_one_or_none():
        slug = f"{slug}-{secrets.token_hex(2)}"

    org = Organization(
        name=organization_name.strip(),
        slug=slug,
        organization_type=organization_type,
        country_code=country_code.upper() if country_code else None,
        email=email_norm,
        settings={
            "features": {
                "mfa_required": False,
                "ai_enabled": True,
            }
        },
    )
    db.add(org)
    await db.flush()

    permissions = await ensure_permission_catalog(db)
    roles = await create_org_system_roles(db, org.id, permissions)

    user = User(
        email=email_norm,
        hashed_password=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        primary_organization_id=org.id,
        email_verified=False,
        password_changed_at=utcnow(),
    )
    db.add(user)
    await db.flush()

    org.created_by_id = user.id
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role_id=roles["org_admin"].id,
        status="active",
        joined_at=utcnow(),
    )
    db.add(membership)
    await db.flush()

    access, refresh = await issue_tokens(
        db,
        user=user,
        organization_id=org.id,
        roles=["org_admin"],
        permissions=[p for p in SYSTEM_ROLES["org_admin"]["permissions"]],
        ip_address=ip_address,
        user_agent=user_agent,
        mfa_verified=False,
    )

    await write_audit_log(
        db,
        action="organization.register",
        resource_type="organization",
        resource_id=org.id,
        organization_id=org.id,
        actor_id=user.id,
        actor_email=user.email,
        description=f"Organization '{org.name}' registered",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return org, user, access, refresh


async def issue_tokens(
    db: AsyncSession,
    *,
    user: User,
    organization_id: Optional[UUID],
    roles: list[str],
    permissions: list[str],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    mfa_verified: bool = False,
) -> tuple[str, str]:
    access = create_access_token(
        user.id,
        organization_id=organization_id,
        roles=roles,
        permissions=permissions,
    )
    raw, token_hash, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            organization_id=organization_id,
            is_mfa_verified=mfa_verified,
        )
    )
    await db.flush()
    return access, raw


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    organization_slug: Optional[str] = None,
    mfa_code: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    email_norm = email.lower().strip()
    result = await db.execute(select(User).where(User.email == email_norm))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("Invalid email or password")

    if user.locked_until and user.locked_until > utcnow():
        raise ForbiddenError("Account temporarily locked. Try again later.")

    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.locked_until = utcnow() + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
        await write_audit_log(
            db,
            action="auth.login_failed",
            resource_type="user",
            resource_id=user.id,
            actor_id=user.id,
            actor_email=user.email,
            description="Failed login attempt",
            ip_address=ip_address,
            user_agent=user_agent,
            status="failure",
        )
        raise UnauthorizedError("Invalid email or password")

    organization: Optional[Organization] = None
    if organization_slug:
        org_result = await db.execute(
            select(Organization).where(Organization.slug == organization_slug)
        )
        organization = org_result.scalar_one_or_none()
        if not organization:
            raise NotFoundError("Organization not found")
    elif user.primary_organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == user.primary_organization_id)
        )
        organization = org_result.scalar_one_or_none()

    roles: list[str] = []
    permissions: list[str] = []
    if organization:
        permissions, role, membership = await get_user_permissions(
            db, user.id, organization.id
        )
        if not membership:
            raise ForbiddenError("You are not a member of this organization")
        if role:
            roles = [role.slug]

    mfa_verified = False
    if user.mfa_enabled:
        if not mfa_code:
            return {
                "mfa_required": True,
                "user": user,
                "organization": organization,
            }
        if not user.mfa_secret_encrypted:
            raise ForbiddenError("MFA is misconfigured for this account")
        secret = decrypt_secret(user.mfa_secret_encrypted)
        if not verify_mfa_code(secret, mfa_code):
            raise UnauthorizedError("Invalid MFA code")
        mfa_verified = True

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = utcnow()

    access, refresh = await issue_tokens(
        db,
        user=user,
        organization_id=organization.id if organization else None,
        roles=roles,
        permissions=permissions,
        ip_address=ip_address,
        user_agent=user_agent,
        mfa_verified=mfa_verified or not user.mfa_enabled,
    )

    await write_audit_log(
        db,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
        organization_id=organization.id if organization else None,
        actor_id=user.id,
        actor_email=user.email,
        description="User logged in",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {
        "mfa_required": False,
        "user": user,
        "organization": organization,
        "access_token": access,
        "refresh_token": refresh,
    }


async def rotate_refresh_token(
    db: AsyncSession,
    *,
    raw_refresh: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[str, str, User, Optional[UUID]]:
    token_hash = hash_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if not stored or not stored.is_active:
        raise UnauthorizedError("Invalid refresh token")

    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User inactive")

    stored.revoked_at = utcnow()
    roles: list[str] = []
    permissions: list[str] = []
    org_id = stored.organization_id
    if org_id:
        permissions, role, _ = await get_user_permissions(db, user.id, org_id)
        if role:
            roles = [role.slug]

    access, new_refresh = await issue_tokens(
        db,
        user=user,
        organization_id=org_id,
        roles=roles,
        permissions=permissions,
        ip_address=ip_address,
        user_agent=user_agent,
        mfa_verified=stored.is_mfa_verified,
    )
    new_hash = hash_token(new_refresh)
    stored.replaced_by_hash = new_hash
    await db.flush()
    return access, new_refresh, user, org_id


async def revoke_refresh_token(db: AsyncSession, raw_refresh: str) -> None:
    token_hash = hash_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    if stored and stored.revoked_at is None:
        stored.revoked_at = utcnow()
        await db.flush()


async def setup_mfa(db: AsyncSession, user: User) -> tuple[str, str]:
    secret = generate_mfa_secret()
    user.mfa_secret_encrypted = encrypt_secret(secret)
    user.mfa_enabled = False
    await db.flush()
    return secret, mfa_provisioning_uri(secret, user.email)


async def enable_mfa(db: AsyncSession, user: User, code: str) -> None:
    if not user.mfa_secret_encrypted:
        raise ForbiddenError("Start MFA setup first")
    secret = decrypt_secret(user.mfa_secret_encrypted)
    if not verify_mfa_code(secret, code):
        raise UnauthorizedError("Invalid MFA code")
    user.mfa_enabled = True
    await write_audit_log(
        db,
        action="auth.mfa_enabled",
        resource_type="user",
        resource_id=user.id,
        organization_id=user.primary_organization_id,
        actor_id=user.id,
        actor_email=user.email,
        description="MFA enabled",
    )


async def disable_mfa(db: AsyncSession, user: User, code: str) -> None:
    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        raise ForbiddenError("MFA is not enabled")
    secret = decrypt_secret(user.mfa_secret_encrypted)
    if not verify_mfa_code(secret, code):
        raise UnauthorizedError("Invalid MFA code")
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    await write_audit_log(
        db,
        action="auth.mfa_disabled",
        resource_type="user",
        resource_id=user.id,
        organization_id=user.primary_organization_id,
        actor_id=user.id,
        actor_email=user.email,
        description="MFA disabled",
    )


async def invite_user(
    db: AsyncSession,
    *,
    organization_id: UUID,
    email: str,
    first_name: str,
    last_name: str,
    role_id: UUID,
    actor: User,
    job_title: Optional[str] = None,
) -> tuple[User, str]:
    role_result = await db.execute(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Role not found in this organization")

    email_norm = email.lower().strip()
    existing = await db.execute(select(User).where(User.email == email_norm))
    user = existing.scalar_one_or_none()
    temp_password = generate_temp_password()

    if user:
        mem_check = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user.id,
            )
        )
        if mem_check.scalar_one_or_none():
            raise ConflictError("User is already a member of this organization")
    else:
        user = User(
            email=email_norm,
            hashed_password=hash_password(temp_password),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            job_title=job_title,
            primary_organization_id=organization_id,
            must_change_password=True,
            password_changed_at=utcnow(),
        )
        db.add(user)
        await db.flush()

    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.id,
        role_id=role.id,
        status="active",
        invited_by_id=actor.id,
        invited_at=utcnow(),
        joined_at=utcnow(),
    )
    db.add(membership)

    await write_audit_log(
        db,
        action="users.invite",
        resource_type="user",
        resource_id=user.id,
        organization_id=organization_id,
        actor_id=actor.id,
        actor_email=actor.email,
        description=f"Invited {user.email} as {role.slug}",
        changes={"role_id": str(role.id)},
    )
    return user, temp_password


async def get_dashboard_stats(db: AsyncSession, organization_id: UUID) -> dict:
    from app.models.audit import AuditLog
    from app.services.programs import phase2_counts
    from app.services.finance import phase3_counts
    from app.services.meal import phase4_counts
    from app.services.beneficiaries import phase5_counts
    from app.services.insights import phase6_counts
    from app.services.ai import phase7_counts
    from app.services.platform import phase8_counts

    users_count = await db.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == "active",
        )
    )
    roles_count = await db.scalar(
        select(func.count()).select_from(Role).where(Role.organization_id == organization_id)
    )
    recent_audit = await db.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.organization_id == organization_id,
            AuditLog.created_at >= utcnow() - timedelta(days=7),
        )
    )
    org = await db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    counts = await phase2_counts(db, organization_id)
    finance_counts = await phase3_counts(db, organization_id)
    meal_counts = await phase4_counts(db, organization_id)
    field_counts = await phase5_counts(db, organization_id)
    insights_counts = await phase6_counts(db, organization_id)
    ai_counts = await phase7_counts(db, organization_id)
    platform_counts = await phase8_counts(db, organization_id)
    return {
        "users_count": users_count or 0,
        "active_memberships": users_count or 0,
        "roles_count": roles_count or 0,
        "recent_audit_events": recent_audit or 0,
        "organization": org,
        **counts,
        **finance_counts,
        **meal_counts,
        **field_counts,
        **insights_counts,
        **ai_counts,
        **platform_counts,
    }
