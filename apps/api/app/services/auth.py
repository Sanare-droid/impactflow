from __future__ import annotations

import asyncio
import logging
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
from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.permissions import PERMISSION_CATALOG, SYSTEM_ROLES
from app.core.security import (
    create_access_token,
    create_email_verify_token,
    create_refresh_token,
    decode_email_verify_token,
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

logger = logging.getLogger(__name__)


async def _send_registration_emails(
    *,
    email: str,
    org_name: str,
    verify_url: str,
) -> None:
    """Best-effort welcome + verify emails — never blocks signup."""
    from app.services import billing_emails

    try:
        await billing_emails.trial_started(email, org_name=org_name, days=14)
    except Exception:  # noqa: BLE001
        logger.exception("registration.trial_email_failed to=%s", email)
    try:
        await billing_emails.email_verification(email, verify_url=verify_url)
    except Exception:  # noqa: BLE001
        logger.exception("registration.verify_email_failed to=%s", email)


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

    # Provision Free Trial subscription + branding + onboarding
    from app.services import enterprise as ent
    from app.services import platform as platform_service

    await ent.get_or_create_subscription(db, org.id, plan_code="free")
    await platform_service.get_branding(db, org.id)
    await ent.get_or_create_onboarding(db, org.id)

    verify_token = create_email_verify_token(user.id)
    frontend = (settings.frontend_url or "").rstrip("/")
    verify_url = f"{frontend}/verify-email?token={verify_token}"

    # Commit before emails so signup is not held open by Resend/SMTP (up to 30s each).
    await db.commit()
    asyncio.create_task(
        _send_registration_emails(
            email=user.email,
            org_name=org.name,
            verify_url=verify_url,
        )
    )

    return org, user, access, refresh


async def verify_email_token(db: AsyncSession, token: str) -> User:
    try:
        user_id = decode_email_verify_token(token)
    except ValueError as exc:
        raise AppError(str(exc), status_code=400) from exc
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")
    user.email_verified = True
    await db.flush()
    return user


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
    send_invite: bool = True,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[User, Optional[str], dict]:
    """Invite a user. Returns (user, temporary_password_or_none, delivery_meta).

    Email is enqueued in the background so invite stays fast under concurrent load.
    """
    from app.services import mailer

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
    temp_password: Optional[str] = None
    created_new = False

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
        temp_password = generate_temp_password()
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
        created_new = True

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

    delivery: dict = {"status": "skipped", "send_invite": send_invite}
    if send_invite:
        from app.services import email_templates

        login_url = f"{settings.frontend_url.rstrip('/')}/login"
        if created_new and temp_password:
            subject, body, html = email_templates.invite_new_user(
                email=user.email,
                temporary_password=temp_password,
                login_url=login_url,
                first_name=user.first_name or first_name,
            )
        else:
            subject, body, html = email_templates.invite_existing_user(
                login_url=login_url,
                first_name=user.first_name or first_name,
            )
        # Do not await provider — keeps invite latency low for concurrent clicks.
        delivery = mailer.enqueue_email(
            to=user.email, subject=subject, body=body, html=html
        )
        delivery["send_invite"] = True

    await write_audit_log(
        db,
        action="users.invite",
        resource_type="user",
        resource_id=user.id,
        organization_id=organization_id,
        actor_id=actor.id,
        actor_email=actor.email,
        description=f"Invited {user.email} as {role.slug}",
        # Never put passwords in audit changes
        changes={
            "role_id": str(role.id),
            "created_new_user": created_new,
            "email_status": delivery.get("status"),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    from app.services.events import EVENT_USER_INVITED, emit_event

    await emit_event(
        db,
        organization_id=organization_id,
        event_type=EVENT_USER_INVITED,
        title=f"User invited: {user.email}",
        body=f"{user.first_name} {user.last_name} joined as {role.name}.",
        link="/app/users",
        severity="info",
        resource_type="user",
        resource_id=str(user.id),
        exclude_user_id=actor.id,
        role_slugs=["org_admin", "manager"],
        metadata={"role": role.slug},
    )
    return user, temp_password, delivery


async def update_membership_role(
    db: AsyncSession,
    *,
    organization_id: UUID,
    membership_id: UUID,
    role_id: UUID,
    actor: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> OrganizationMembership:
    membership = await db.scalar(
        select(OrganizationMembership)
        .options(
            selectinload(OrganizationMembership.user),
            selectinload(OrganizationMembership.role),
        )
        .where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if not membership:
        raise NotFoundError("Membership not found")

    role = await db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == organization_id,
        )
    )
    if not role:
        raise NotFoundError("Role not found in this organization")

    previous_role_id = membership.role_id
    previous_slug = membership.role.slug if membership.role else None
    if previous_role_id == role.id:
        return membership

    membership.role_id = role.id
    await db.flush()
    await db.refresh(membership, attribute_names=["role", "user"])

    await write_audit_log(
        db,
        action="users.role_change",
        resource_type="membership",
        resource_id=membership.id,
        organization_id=organization_id,
        actor_id=actor.id,
        actor_email=actor.email,
        description=f"Changed role for {membership.user.email if membership.user else membership.user_id} to {role.slug}",
        changes={
            "previous_role_id": str(previous_role_id),
            "previous_role": previous_slug,
            "role_id": str(role.id),
            "role": role.slug,
            "user_id": str(membership.user_id),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return membership


def _validate_password_strength(password: str) -> str:
    if len(password) < settings.password_min_length:
        raise AppError(
            f"Password must be at least {settings.password_min_length} characters",
            code="weak_password",
        )
    if not any(c.isupper() for c in password):
        raise AppError("Password must contain an uppercase letter", code="weak_password")
    if not any(c.islower() for c in password):
        raise AppError("Password must contain a lowercase letter", code="weak_password")
    if not any(c.isdigit() for c in password):
        raise AppError("Password must contain a digit", code="weak_password")
    return password


async def change_password(
    db: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    if not verify_password(current_password, user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")
    new_password = _validate_password_strength(new_password)
    if verify_password(new_password, user.hashed_password):
        raise AppError("New password must be different from the current password")
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = utcnow()
    await db.flush()
    await write_audit_log(
        db,
        action="auth.password_change",
        resource_type="user",
        resource_id=user.id,
        organization_id=user.primary_organization_id,
        actor_id=user.id,
        actor_email=user.email,
        description="Password changed",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user


async def request_password_reset(
    db: AsyncSession,
    *,
    email: str,
    ip_address: Optional[str] = None,
) -> dict:
    """Always returns a generic message; emails only if user exists."""
    from app.models.password_reset import PasswordResetToken
    from app.services.mailer import send_email

    email_norm = email.lower().strip()
    user = await db.scalar(select(User).where(User.email == email_norm, User.is_active.is_(True)))
    if user:
        raw = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=utcnow() + timedelta(hours=1),
            requested_ip=ip_address,
        )
        db.add(token)
        await db.flush()
        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw}"
        from app.services import email_templates

        subject, body, html = email_templates.password_reset(
            reset_url=reset_url,
            first_name=user.first_name or "",
        )
        await send_email(
            to=user.email,
            subject=subject,
            body=body,
            html=html,
        )
        await write_audit_log(
            db,
            action="auth.password_reset_request",
            resource_type="user",
            resource_id=user.id,
            organization_id=user.primary_organization_id,
            actor_id=user.id,
            actor_email=user.email,
            description="Password reset requested",
            ip_address=ip_address,
        )
    return {
        "message": "If an account exists for that email, password reset instructions were sent."
    }


async def reset_password(
    db: AsyncSession,
    *,
    token: str,
    new_password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    from app.models.password_reset import PasswordResetToken

    new_password = _validate_password_strength(new_password)
    token_hash = hash_token(token)
    row = await db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    )
    if not row or row.expires_at < utcnow():
        raise AppError("Invalid or expired reset token", code="invalid_reset_token")
    user = await db.get(User, row.user_id)
    if not user or not user.is_active:
        raise NotFoundError("User not found")
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    row.used_at = utcnow()
    await db.flush()
    await write_audit_log(
        db,
        action="auth.password_reset",
        resource_type="user",
        resource_id=user.id,
        organization_id=user.primary_organization_id,
        actor_id=user.id,
        actor_email=user.email,
        description="Password reset completed",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user


async def get_dashboard_stats(db: AsyncSession, organization_id: UUID) -> dict:
    from app.models.audit import AuditLog
    from app.services.programs import phase2_counts
    from app.services.finance import phase3_counts
    from app.services.meal import phase4_counts
    from app.services.beneficiaries import phase5_counts
    from app.services.insights import phase6_counts
    from app.services.ai import phase7_counts
    from app.services.platform import phase8_counts
    from app.services.notifications import phase10_counts
    from app.services.surveys import phase11_survey_counts

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
    notify_counts = await phase10_counts(db, organization_id)
    survey_counts = await phase11_survey_counts(db, organization_id)
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
        **notify_counts,
        **survey_counts,
    }


async def start_sso_login(
    db: AsyncSession,
    *,
    organization_slug: str,
    redirect_uri: str,
) -> dict:
    """Build OIDC authorize URL for an organization's SSO configuration."""
    from urllib.parse import urlencode
    from uuid import uuid4

    from app.models.enterprise import SsoConfiguration

    slug = organization_slug.strip().lower()
    org = await db.scalar(select(Organization).where(Organization.slug == slug))
    if not org:
        raise NotFoundError("Organization not found")
    sso = await db.scalar(
        select(SsoConfiguration).where(
            SsoConfiguration.organization_id == org.id,
            SsoConfiguration.status.in_(("active", "enabled", "draft")),
        )
    )
    if not sso:
        raise NotFoundError("SSO is not configured for this organization")
    cfg = dict(sso.config or {})
    authorize = cfg.get("authorize_url") or cfg.get("authorization_endpoint")
    client_id = cfg.get("client_id")
    if not authorize or not client_id:
        raise AppError(
            "SSO config missing authorize_url / client_id",
            code="sso_misconfigured",
        )
    state = f"{org.id}:{uuid4().hex}"
    meta = dict(sso.metadata_ or {})
    meta["pending_oauth_state"] = state
    meta["pending_redirect_uri"] = redirect_uri
    sso.metadata_ = meta
    await db.flush()
    scopes = cfg.get("scopes") or ["openid", "email", "profile"]
    if isinstance(scopes, str):
        scope = scopes
    else:
        scope = " ".join(scopes)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope,
    }
    sep = "&" if "?" in authorize else "?"
    return {
        "authorize_url": f"{authorize}{sep}{urlencode(params)}",
        "state": state,
        "organization_id": str(org.id),
        "provider": sso.provider,
    }


async def complete_sso_login(
    db: AsyncSession,
    *,
    code: str,
    state: str,
    redirect_uri: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    """Exchange OIDC code, find/create user membership, issue ImpactFlow tokens."""
    import httpx

    from app.models.enterprise import SsoConfiguration

    parts = (state or "").split(":")
    if len(parts) < 1:
        raise AppError("Invalid SSO state", code="VALIDATION_ERROR")
    try:
        org_id = UUID(parts[0])
    except ValueError as exc:
        raise AppError("Invalid SSO state", code="VALIDATION_ERROR") from exc

    sso = await db.scalar(
        select(SsoConfiguration).where(SsoConfiguration.organization_id == org_id)
    )
    if not sso:
        raise NotFoundError("SSO configuration not found")
    meta = dict(sso.metadata_ or {})
    if meta.get("pending_oauth_state") and meta["pending_oauth_state"] != state:
        raise AppError("SSO state mismatch", code="sso_state_mismatch")
    redirect = redirect_uri or meta.get("pending_redirect_uri")
    if not redirect:
        raise AppError("redirect_uri required", code="VALIDATION_ERROR")

    cfg = dict(sso.config or {})
    secrets = dict(sso.secrets_ or {})
    token_url = cfg.get("token_url") or cfg.get("token_endpoint")
    client_id = cfg.get("client_id")
    client_secret = secrets.get("client_secret") or cfg.get("client_secret")
    if not token_url or not client_id:
        raise AppError("SSO token endpoint / client_id missing", code="sso_misconfigured")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
        "client_id": client_id,
    }
    if client_secret:
        data["client_secret"] = client_secret
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code >= 400:
            raise AppError(f"SSO token exchange failed: {resp.text[:300]}", code="sso_exchange_failed")
        tokens = resp.json()

    email = None
    # Prefer userinfo endpoint when configured
    userinfo_url = cfg.get("userinfo_url") or cfg.get("userinfo_endpoint")
    access = tokens.get("access_token")
    if userinfo_url and access:
        async with httpx.AsyncClient(timeout=20.0) as client:
            ui = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access}"},
            )
            if ui.status_code < 400:
                profile = ui.json()
                email = profile.get("email")
    if not email and tokens.get("id_token"):
        # Decode JWT payload without verifying signature (IdP already issued it over TLS).
        import base64
        import json as json_lib

        try:
            payload_b64 = tokens["id_token"].split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            claims = json_lib.loads(base64.urlsafe_b64decode(payload_b64.encode()))
            email = claims.get("email") or claims.get("preferred_username")
        except Exception:  # noqa: BLE001
            email = None
    if not email:
        raise AppError("SSO provider did not return an email claim", code="sso_no_email")

    email_norm = str(email).lower().strip()
    user = await db.scalar(select(User).where(User.email == email_norm))
    if not user:
        raise ForbiddenError(
            "No ImpactFlow account for this SSO email. Ask an admin to invite you first."
        )
    permissions, role, membership = await get_user_permissions(db, user.id, org_id)
    if not membership:
        raise ForbiddenError("You are not a member of this organization")
    roles = [role.slug] if role else []

    user.last_login_at = utcnow()
    access_token, refresh_token = await issue_tokens(
        db,
        user=user,
        organization_id=org_id,
        roles=roles,
        permissions=permissions,
        ip_address=ip_address,
        user_agent=user_agent,
        mfa_verified=True,
    )
    meta.pop("pending_oauth_state", None)
    sso.metadata_ = meta
    sso.status = "active"
    await db.flush()
    await write_audit_log(
        db,
        action="auth.sso_login",
        resource_type="user",
        resource_id=user.id,
        organization_id=org_id,
        actor_id=user.id,
        actor_email=user.email,
        description=f"SSO login via {sso.provider}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    org = await db.get(Organization, org_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "mfa_required": False,
        "user": user,
        "organization": org,
    }
