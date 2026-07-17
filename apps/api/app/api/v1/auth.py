from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, get_current_context
from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MFAEnableRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MessageResponse,
    RefreshRequest,
    RegisterOrganizationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserBrief,
    UserResponse,
)
from app.services import auth as auth_service
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterOrganizationRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    ip, ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:register:{ip}", limit=5, window_seconds=3600)
    org, user, access, refresh = await auth_service.register_organization(
        db,
        organization_name=body.organization_name,
        organization_slug=body.organization_slug,
        organization_type=body.organization_type,
        country_code=body.country_code,
        email=str(body.email),
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        ip_address=ip,
        user_agent=ua,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserBrief.model_validate(user),
        organization_id=org.id,
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    token = (body or {}).get("token") or ""
    if not token:
        from app.core.exceptions import AppError

        raise AppError("Verification token required", status_code=400)
    await auth_service.verify_email_token(db, str(token))
    return MessageResponse(message="Email verified successfully")


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    ip, ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:login:{ip}", limit=30, window_seconds=60)
    await enforce_rate_limit(
        key=f"rl:login:email:{str(body.email).lower()}", limit=10, window_seconds=60
    )
    result = await auth_service.authenticate_user(
        db,
        email=str(body.email),
        password=body.password,
        organization_slug=body.organization_slug,
        mfa_code=body.mfa_code,
        ip_address=ip,
        user_agent=ua,
    )
    if result.get("mfa_required"):
        return TokenResponse(
            access_token="",
            refresh_token="",
            expires_in=0,
            mfa_required=True,
            user=UserBrief.model_validate(result["user"]),
        )
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserBrief.model_validate(result["user"]),
        organization_id=result["organization"].id if result.get("organization") else None,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    ip, ua = client_meta(request)
    access, refresh_token, user, org_id = await auth_service.rotate_refresh_token(
        db,
        raw_refresh=body.refresh_token,
        ip_address=ip,
        user_agent=ua,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserBrief.model_validate(user),
        organization_id=org_id,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    await auth_service.revoke_refresh_token(db, body.refresh_token)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
) -> UserResponse:
    if ctx.auth_method == "api_key":
        raise ForbiddenError("API keys cannot use /auth/me")
    return UserResponse.model_validate(ctx.user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("Password change requires user session")
    ip, ua = client_meta(request)
    await auth_service.change_password(
        db,
        user=ctx.user,
        current_password=body.current_password,
        new_password=body.new_password,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Password updated")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    ip, _ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:forgot:{ip}", limit=10, window_seconds=3600)
    result = await auth_service.request_password_reset(
        db, email=str(body.email), ip_address=ip
    )
    return MessageResponse(message=result["message"])


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    ip, ua = client_meta(request)
    await enforce_rate_limit(key=f"rl:reset:{ip}", limit=20, window_seconds=3600)
    await auth_service.reset_password(
        db,
        token=body.token,
        new_password=body.new_password,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Password has been reset. You can sign in now.")


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MFASetupResponse:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("MFA requires user session")
    secret, uri = await auth_service.setup_mfa(db, ctx.user)
    return MFASetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/mfa/enable", response_model=MessageResponse)
async def mfa_enable(
    body: MFAEnableRequest,
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("MFA requires user session")
    await auth_service.enable_mfa(db, ctx.user, body.code)
    return MessageResponse(message="MFA enabled")


@router.post("/mfa/disable", response_model=MessageResponse)
async def mfa_disable(
    body: MFAVerifyRequest,
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    if ctx.auth_method != "jwt":
        raise ForbiddenError("MFA requires user session")
    await auth_service.disable_mfa(db, ctx.user, body.code)
    return MessageResponse(message="MFA disabled")


@router.get("/sso/start")
async def sso_start(
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_slug: str,
    redirect_uri: str,
) -> dict:
    return await auth_service.start_sso_login(
        db,
        organization_slug=organization_slug,
        redirect_uri=redirect_uri,
    )


@router.post("/sso/callback", response_model=TokenResponse)
async def sso_callback(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str,
    state: str,
    redirect_uri: str | None = None,
) -> TokenResponse:
    ip, ua = client_meta(request)
    result = await auth_service.complete_sso_login(
        db,
        code=code,
        state=state,
        redirect_uri=redirect_uri,
        ip_address=ip,
        user_agent=ua,
    )
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=result["expires_in"],
        user=UserBrief.model_validate(result["user"]),
        organization_id=result["organization"].id if result.get("organization") else None,
    )
