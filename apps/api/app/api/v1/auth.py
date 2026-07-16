from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_meta, get_current_context, RequestContext
from app.core.config import settings
from app.db.session import get_db
from app.schemas import (
    LoginRequest,
    MFAEnableRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MessageResponse,
    RefreshRequest,
    RegisterOrganizationRequest,
    TokenResponse,
    UserBrief,
    UserResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterOrganizationRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    ip, ua = client_meta(request)
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
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    ip, ua = client_meta(request)
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
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    ip, ua = client_meta(request)
    access, refresh_token, user, _org_id = await auth_service.rotate_refresh_token(
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
    return UserResponse.model_validate(ctx.user)


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MFASetupResponse:
    secret, uri = await auth_service.setup_mfa(db, ctx.user)
    return MFASetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/mfa/enable", response_model=MessageResponse)
async def mfa_enable(
    body: MFAEnableRequest,
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    await auth_service.enable_mfa(db, ctx.user, body.code)
    return MessageResponse(message="MFA enabled")


@router.post("/mfa/disable", response_model=MessageResponse)
async def mfa_disable(
    body: MFAVerifyRequest,
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    await auth_service.disable_mfa(db, ctx.user, body.code)
    return MessageResponse(message="MFA disabled")
