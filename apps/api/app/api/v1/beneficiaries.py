from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import (
    BeneficiaryCreateRequest,
    BeneficiaryMembershipCreateRequest,
    BeneficiaryMembershipResponse,
    BeneficiaryMembershipUpdateRequest,
    BeneficiaryResponse,
    BeneficiaryUpdateRequest,
    CommunityCreateRequest,
    CommunityResponse,
    CommunityUpdateRequest,
    HouseholdCreateRequest,
    HouseholdResponse,
    HouseholdUpdateRequest,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.services import beneficiaries as beneficiary_service

router = APIRouter(tags=["Beneficiaries & Field"])


def _meta(page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


def _require_org(ctx: RequestContext) -> UUID:
    if not ctx.organization:
        raise NotFoundError("No active organization context")
    return ctx.organization.id


# -------- Communities --------


@router.get("/communities", response_model=PaginatedResponse[CommunityResponse])
async def list_communities(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("communities:read", "communities:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    updated_after: Optional[datetime] = Query(None),
) -> PaginatedResponse[CommunityResponse]:
    org_id = _require_org(ctx)
    items, total = await beneficiary_service.list_communities(
        db,
        org_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        updated_after=updated_after,
    )
    return PaginatedResponse(
        items=[CommunityResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/communities", response_model=CommunityResponse, status_code=201)
async def create_community(
    body: CommunityCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("communities:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommunityResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    community = await beneficiary_service.create_community(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return CommunityResponse.model_validate(community)


@router.get("/communities/{community_id}", response_model=CommunityResponse)
async def get_community(
    community_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("communities:read", "communities:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommunityResponse:
    org_id = _require_org(ctx)
    community = await beneficiary_service.get_community(db, org_id, community_id)
    return CommunityResponse.model_validate(community)


@router.patch("/communities/{community_id}", response_model=CommunityResponse)
async def update_community(
    community_id: UUID,
    body: CommunityUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("communities:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommunityResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    community = await beneficiary_service.get_community(db, org_id, community_id)
    updated = await beneficiary_service.update_community(
        db,
        community,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return CommunityResponse.model_validate(updated)


@router.delete("/communities/{community_id}", response_model=MessageResponse)
async def delete_community(
    community_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("communities:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    community = await beneficiary_service.get_community(db, org_id, community_id)
    await beneficiary_service.delete_community(
        db,
        community,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Community deleted")


# -------- Households --------


@router.get("/households", response_model=PaginatedResponse[HouseholdResponse])
async def list_households(
    ctx: Annotated[
        RequestContext, Depends(require_permissions("households:read", "households:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    community_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    updated_after: Optional[datetime] = Query(None),
) -> PaginatedResponse[HouseholdResponse]:
    org_id = _require_org(ctx)
    items, total = await beneficiary_service.list_households(
        db,
        org_id,
        page=page,
        page_size=page_size,
        community_id=community_id,
        status=status,
        search=search,
        updated_after=updated_after,
    )
    return PaginatedResponse(
        items=[HouseholdResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/households", response_model=HouseholdResponse, status_code=201)
async def create_household(
    body: HouseholdCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("households:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HouseholdResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    household = await beneficiary_service.create_household(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return HouseholdResponse.model_validate(household)


@router.get("/households/{household_id}", response_model=HouseholdResponse)
async def get_household(
    household_id: UUID,
    ctx: Annotated[
        RequestContext, Depends(require_permissions("households:read", "households:manage"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HouseholdResponse:
    org_id = _require_org(ctx)
    household = await beneficiary_service.get_household(db, org_id, household_id)
    return HouseholdResponse.model_validate(household)


@router.patch("/households/{household_id}", response_model=HouseholdResponse)
async def update_household(
    household_id: UUID,
    body: HouseholdUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("households:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HouseholdResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    household = await beneficiary_service.get_household(db, org_id, household_id)
    updated = await beneficiary_service.update_household(
        db,
        household,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return HouseholdResponse.model_validate(updated)


@router.delete("/households/{household_id}", response_model=MessageResponse)
async def delete_household(
    household_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("households:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    household = await beneficiary_service.get_household(db, org_id, household_id)
    await beneficiary_service.delete_household(
        db,
        household,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Household deleted")


# -------- Beneficiaries --------


@router.get("/beneficiaries", response_model=PaginatedResponse[BeneficiaryResponse])
async def list_beneficiaries(
    ctx: Annotated[
        RequestContext,
        Depends(require_permissions("beneficiaries:read", "beneficiaries:manage")),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    household_id: Optional[UUID] = None,
    community_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    updated_after: Optional[datetime] = Query(None),
) -> PaginatedResponse[BeneficiaryResponse]:
    org_id = _require_org(ctx)
    items, total = await beneficiary_service.list_beneficiaries(
        db,
        org_id,
        page=page,
        page_size=page_size,
        household_id=household_id,
        community_id=community_id,
        status=status,
        search=search,
        updated_after=updated_after,
    )
    return PaginatedResponse(
        items=[BeneficiaryResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/beneficiaries", response_model=BeneficiaryResponse, status_code=201)
async def create_beneficiary(
    body: BeneficiaryCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("beneficiaries:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BeneficiaryResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    from app.services import enterprise as ent

    await ent.enforce_writable(db, org_id)
    beneficiary = await beneficiary_service.create_beneficiary(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return BeneficiaryResponse.model_validate(beneficiary)


@router.get("/beneficiaries/{beneficiary_id}", response_model=BeneficiaryResponse)
async def get_beneficiary(
    beneficiary_id: UUID,
    ctx: Annotated[
        RequestContext,
        Depends(require_permissions("beneficiaries:read", "beneficiaries:manage")),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BeneficiaryResponse:
    org_id = _require_org(ctx)
    beneficiary = await beneficiary_service.get_beneficiary(db, org_id, beneficiary_id)
    return BeneficiaryResponse.model_validate(beneficiary)


@router.patch("/beneficiaries/{beneficiary_id}", response_model=BeneficiaryResponse)
async def update_beneficiary(
    beneficiary_id: UUID,
    body: BeneficiaryUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("beneficiaries:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BeneficiaryResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    beneficiary = await beneficiary_service.get_beneficiary(db, org_id, beneficiary_id)
    updated = await beneficiary_service.update_beneficiary(
        db,
        beneficiary,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return BeneficiaryResponse.model_validate(updated)


@router.delete("/beneficiaries/{beneficiary_id}", response_model=MessageResponse)
async def delete_beneficiary(
    beneficiary_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("beneficiaries:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    beneficiary = await beneficiary_service.get_beneficiary(db, org_id, beneficiary_id)
    await beneficiary_service.delete_beneficiary(
        db,
        beneficiary,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Beneficiary deleted")


@router.post(
    "/beneficiaries/{beneficiary_id}/memberships",
    response_model=BeneficiaryMembershipResponse,
    status_code=201,
)
async def add_membership(
    beneficiary_id: UUID,
    body: BeneficiaryMembershipCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("beneficiaries:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BeneficiaryMembershipResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    beneficiary = await beneficiary_service.get_beneficiary(db, org_id, beneficiary_id)
    membership = await beneficiary_service.add_membership(
        db,
        beneficiary,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return BeneficiaryMembershipResponse.model_validate(membership)


@router.get(
    "/beneficiary-memberships",
    response_model=PaginatedResponse[BeneficiaryMembershipResponse],
)
async def list_memberships(
    ctx: Annotated[
        RequestContext,
        Depends(require_permissions("beneficiaries:read", "beneficiaries:manage")),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    beneficiary_id: Optional[UUID] = None,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> PaginatedResponse[BeneficiaryMembershipResponse]:
    org_id = _require_org(ctx)
    items, total = await beneficiary_service.list_memberships(
        db,
        org_id,
        page=page,
        page_size=page_size,
        beneficiary_id=beneficiary_id,
        program_id=program_id,
        project_id=project_id,
        status=status,
    )
    return PaginatedResponse(
        items=[BeneficiaryMembershipResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.patch(
    "/beneficiary-memberships/{membership_id}",
    response_model=BeneficiaryMembershipResponse,
)
async def update_membership(
    membership_id: UUID,
    body: BeneficiaryMembershipUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("beneficiaries:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BeneficiaryMembershipResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    membership = await beneficiary_service.get_membership(db, org_id, membership_id)
    updated = await beneficiary_service.update_membership(
        db,
        membership,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return BeneficiaryMembershipResponse.model_validate(updated)
