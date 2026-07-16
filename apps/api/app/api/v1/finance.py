from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequestContext, client_meta, require_permissions
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas import (
    BudgetCreateRequest,
    BudgetLineCreateRequest,
    BudgetLineResponse,
    BudgetResponse,
    BudgetUpdateRequest,
    DonorCreateRequest,
    DonorResponse,
    DonorUpdateRequest,
    FinanceTransactionCreateRequest,
    FinanceTransactionResponse,
    FinanceTransactionUpdateRequest,
    GrantCreateRequest,
    GrantResponse,
    GrantUpdateRequest,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
)
from app.services import finance as finance_service

router = APIRouter(tags=["Grants & Finance"])


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


# -------- Donors --------


@router.get("/donors", response_model=PaginatedResponse[DonorResponse])
async def list_donors(
    ctx: Annotated[RequestContext, Depends(require_permissions("donors:read", "donors:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[DonorResponse]:
    org_id = _require_org(ctx)
    items, total = await finance_service.list_donors(
        db, org_id, page=page, page_size=page_size, status=status, search=search
    )
    return PaginatedResponse(
        items=[DonorResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/donors", response_model=DonorResponse, status_code=201)
async def create_donor(
    body: DonorCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("donors:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DonorResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    donor = await finance_service.create_donor(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return DonorResponse.model_validate(donor)


@router.get("/donors/{donor_id}", response_model=DonorResponse)
async def get_donor(
    donor_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("donors:read", "donors:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DonorResponse:
    org_id = _require_org(ctx)
    donor = await finance_service.get_donor(db, org_id, donor_id)
    return DonorResponse.model_validate(donor)


@router.patch("/donors/{donor_id}", response_model=DonorResponse)
async def update_donor(
    donor_id: UUID,
    body: DonorUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("donors:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DonorResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    donor = await finance_service.get_donor(db, org_id, donor_id)
    updated = await finance_service.update_donor(
        db,
        donor,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return DonorResponse.model_validate(updated)


@router.delete("/donors/{donor_id}", response_model=MessageResponse)
async def delete_donor(
    donor_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("donors:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    donor = await finance_service.get_donor(db, org_id, donor_id)
    await finance_service.delete_donor(
        db,
        donor,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Donor deleted")


# -------- Grants --------


@router.get("/grants", response_model=PaginatedResponse[GrantResponse])
async def list_grants(
    ctx: Annotated[RequestContext, Depends(require_permissions("grants:read", "grants:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    donor_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> PaginatedResponse[GrantResponse]:
    org_id = _require_org(ctx)
    items, total = await finance_service.list_grants(
        db,
        org_id,
        page=page,
        page_size=page_size,
        donor_id=donor_id,
        status=status,
        search=search,
    )
    return PaginatedResponse(
        items=[GrantResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/grants", response_model=GrantResponse, status_code=201)
async def create_grant(
    body: GrantCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("grants:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GrantResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    grant = await finance_service.create_grant(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return GrantResponse.model_validate(grant)


@router.get("/grants/{grant_id}", response_model=GrantResponse)
async def get_grant(
    grant_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("grants:read", "grants:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GrantResponse:
    org_id = _require_org(ctx)
    grant = await finance_service.get_grant(db, org_id, grant_id)
    return GrantResponse.model_validate(grant)


@router.patch("/grants/{grant_id}", response_model=GrantResponse)
async def update_grant(
    grant_id: UUID,
    body: GrantUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("grants:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GrantResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    grant = await finance_service.get_grant(db, org_id, grant_id)
    updated = await finance_service.update_grant(
        db,
        grant,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return GrantResponse.model_validate(updated)


@router.delete("/grants/{grant_id}", response_model=MessageResponse)
async def delete_grant(
    grant_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("grants:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    grant = await finance_service.get_grant(db, org_id, grant_id)
    await finance_service.delete_grant(
        db,
        grant,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Grant deleted")


# -------- Budgets --------


@router.get("/budgets", response_model=PaginatedResponse[BudgetResponse])
async def list_budgets(
    ctx: Annotated[RequestContext, Depends(require_permissions("budgets:read", "budgets:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    grant_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> PaginatedResponse[BudgetResponse]:
    org_id = _require_org(ctx)
    items, total = await finance_service.list_budgets(
        db,
        org_id,
        page=page,
        page_size=page_size,
        grant_id=grant_id,
        project_id=project_id,
        status=status,
    )
    return PaginatedResponse(
        items=[BudgetResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/budgets", response_model=BudgetResponse, status_code=201)
async def create_budget(
    body: BudgetCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("budgets:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    payload = body.model_dump()
    lines = payload.pop("lines", None)
    budget = await finance_service.create_budget(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=payload,
        lines=lines,
        ip_address=ip,
        user_agent=ua,
    )
    return BudgetResponse.model_validate(budget)


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: UUID,
    ctx: Annotated[RequestContext, Depends(require_permissions("budgets:read", "budgets:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetResponse:
    org_id = _require_org(ctx)
    budget = await finance_service.get_budget(db, org_id, budget_id, with_lines=True)
    return BudgetResponse.model_validate(budget)


@router.patch("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: UUID,
    body: BudgetUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("budgets:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    budget = await finance_service.get_budget(db, org_id, budget_id)
    updated = await finance_service.update_budget(
        db,
        budget,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return BudgetResponse.model_validate(
        await finance_service.get_budget(db, org_id, updated.id, with_lines=True)
    )


@router.post("/budgets/{budget_id}/lines", response_model=BudgetLineResponse, status_code=201)
async def add_budget_line(
    budget_id: UUID,
    body: BudgetLineCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("budgets:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetLineResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    budget = await finance_service.get_budget(db, org_id, budget_id)
    line = await finance_service.add_budget_line(
        db,
        budget,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return BudgetLineResponse.model_validate(line)


@router.delete("/budgets/{budget_id}", response_model=MessageResponse)
async def delete_budget(
    budget_id: UUID,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("budgets:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    budget = await finance_service.get_budget(db, org_id, budget_id)
    await finance_service.delete_budget(
        db,
        budget,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        ip_address=ip,
        user_agent=ua,
    )
    return MessageResponse(message="Budget deleted")


# -------- Finance transactions --------


@router.get("/finance/transactions", response_model=PaginatedResponse[FinanceTransactionResponse])
async def list_transactions(
    ctx: Annotated[RequestContext, Depends(require_permissions("finance:read", "finance:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    grant_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    budget_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
) -> PaginatedResponse[FinanceTransactionResponse]:
    org_id = _require_org(ctx)
    items, total = await finance_service.list_transactions(
        db,
        org_id,
        page=page,
        page_size=page_size,
        grant_id=grant_id,
        project_id=project_id,
        budget_id=budget_id,
        transaction_type=transaction_type,
    )
    return PaginatedResponse(
        items=[FinanceTransactionResponse.model_validate(i) for i in items],
        meta=_meta(page, page_size, total),
    )


@router.post("/finance/transactions", response_model=FinanceTransactionResponse, status_code=201)
async def create_transaction(
    body: FinanceTransactionCreateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("finance:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinanceTransactionResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    txn = await finance_service.create_transaction(
        db,
        organization_id=org_id,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    return FinanceTransactionResponse.model_validate(txn)


@router.patch(
    "/finance/transactions/{transaction_id}",
    response_model=FinanceTransactionResponse,
)
async def update_transaction(
    transaction_id: UUID,
    body: FinanceTransactionUpdateRequest,
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_permissions("finance:manage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinanceTransactionResponse:
    org_id = _require_org(ctx)
    ip, ua = client_meta(request)
    txn = await finance_service.get_transaction(db, org_id, transaction_id)
    updated = await finance_service.update_transaction(
        db,
        txn,
        actor_id=ctx.user.id,
        actor_email=ctx.user.email,
        data=body.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return FinanceTransactionResponse.model_validate(updated)
