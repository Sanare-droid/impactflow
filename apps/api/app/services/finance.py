from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.budget import Budget, BudgetLine
from app.models.donor import Donor
from app.models.finance import FinanceTransaction
from app.models.grant import Grant
from app.models.program import Program
from app.models.project import Project
from app.services.audit import write_audit_log
from app.services.programs import make_code, _ensure_unique_code


def _dec(value: Optional[Decimal | float | int | str]) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


async def get_donor(db: AsyncSession, organization_id: UUID, donor_id: UUID) -> Donor:
    donor = await db.scalar(
        select(Donor).where(Donor.id == donor_id, Donor.organization_id == organization_id)
    )
    if not donor:
        raise NotFoundError("Donor not found")
    return donor


async def list_donors(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Donor], int]:
    filters = [Donor.organization_id == organization_id]
    if status:
        filters.append(Donor.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append((Donor.name.ilike(like)) | (Donor.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Donor).where(*filters)) or 0
    result = await db.execute(
        select(Donor)
        .where(*filters)
        .order_by(Donor.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_donor(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Donor:
    code = await _ensure_unique_code(
        db,
        model=Donor,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"]),
    )
    donor = Donor(
        organization_id=organization_id,
        name=data["name"].strip(),
        code=code,
        donor_type=data.get("donor_type") or "foundation",
        status=data.get("status") or "active",
        country_code=(data.get("country_code") or "").upper() or None,
        contact_name=data.get("contact_name"),
        contact_email=data.get("contact_email"),
        contact_phone=data.get("contact_phone"),
        website=data.get("website"),
        notes=data.get("notes"),
        created_by_id=actor_id,
    )
    db.add(donor)
    await db.flush()
    await write_audit_log(
        db,
        action="donors.create",
        resource_type="donor",
        resource_id=donor.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created donor {donor.code}",
        changes={"name": donor.name, "code": donor.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return donor


async def update_donor(
    db: AsyncSession,
    donor: Donor,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Donor:
    if "code" in data and data["code"]:
        new_code = make_code(data["code"])
        if new_code != donor.code:
            data["code"] = await _ensure_unique_code(
                db, model=Donor, organization_id=donor.organization_id, code=new_code
            )
    if "country_code" in data and data["country_code"]:
        data["country_code"] = data["country_code"].upper()
    for key, value in data.items():
        setattr(donor, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="donors.update",
        resource_type="donor",
        resource_id=donor.id,
        organization_id=donor.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated donor {donor.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return donor


async def delete_donor(
    db: AsyncSession,
    donor: Donor,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="donors.delete",
        resource_type="donor",
        resource_id=donor.id,
        organization_id=donor.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted donor {donor.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(donor)
    await db.flush()


async def get_grant(db: AsyncSession, organization_id: UUID, grant_id: UUID) -> Grant:
    grant = await db.scalar(
        select(Grant).where(Grant.id == grant_id, Grant.organization_id == organization_id)
    )
    if not grant:
        raise NotFoundError("Grant not found")
    return grant


async def list_grants(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    donor_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Grant], int]:
    filters = [Grant.organization_id == organization_id]
    if donor_id:
        filters.append(Grant.donor_id == donor_id)
    if status:
        filters.append(Grant.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append((Grant.name.ilike(like)) | (Grant.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Grant).where(*filters)) or 0
    result = await db.execute(
        select(Grant)
        .where(*filters)
        .order_by(Grant.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_grant(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Grant:
    await get_donor(db, organization_id, data["donor_id"])
    if data.get("program_id"):
        exists = await db.scalar(
            select(Program.id).where(
                Program.id == data["program_id"],
                Program.organization_id == organization_id,
            )
        )
        if not exists:
            raise NotFoundError("Program not found")
    if data.get("project_id"):
        exists = await db.scalar(
            select(Project.id).where(
                Project.id == data["project_id"],
                Project.organization_id == organization_id,
            )
        )
        if not exists:
            raise NotFoundError("Project not found")

    code = await _ensure_unique_code(
        db,
        model=Grant,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"]),
    )
    grant = Grant(
        organization_id=organization_id,
        donor_id=data["donor_id"],
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        name=data["name"].strip(),
        code=code,
        description=data.get("description"),
        status=data.get("status") or "pipeline",
        currency=(data.get("currency") or "USD").upper(),
        amount_awarded=_dec(data.get("amount_awarded")),
        amount_received=_dec(data.get("amount_received")),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        agreement_reference=data.get("agreement_reference"),
        created_by_id=actor_id,
    )
    db.add(grant)
    await db.flush()
    await write_audit_log(
        db,
        action="grants.create",
        resource_type="grant",
        resource_id=grant.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created grant {grant.code}",
        changes={"name": grant.name, "donor_id": str(grant.donor_id)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return grant


async def update_grant(
    db: AsyncSession,
    grant: Grant,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Grant:
    if "donor_id" in data and data["donor_id"]:
        await get_donor(db, grant.organization_id, data["donor_id"])
    if "code" in data and data["code"]:
        new_code = make_code(data["code"])
        if new_code != grant.code:
            data["code"] = await _ensure_unique_code(
                db, model=Grant, organization_id=grant.organization_id, code=new_code
            )
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    for key in ("amount_awarded", "amount_received"):
        if key in data:
            data[key] = _dec(data[key])
    for key, value in data.items():
        setattr(grant, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="grants.update",
        resource_type="grant",
        resource_id=grant.id,
        organization_id=grant.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated grant {grant.code}",
        changes={k: str(v) for k, v in data.items()},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return grant


async def delete_grant(
    db: AsyncSession,
    grant: Grant,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="grants.delete",
        resource_type="grant",
        resource_id=grant.id,
        organization_id=grant.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted grant {grant.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(grant)
    await db.flush()


async def get_budget(
    db: AsyncSession, organization_id: UUID, budget_id: UUID, *, with_lines: bool = False
) -> Budget:
    stmt = select(Budget).where(
        Budget.id == budget_id, Budget.organization_id == organization_id
    )
    if with_lines:
        stmt = stmt.options(selectinload(Budget.lines))
    budget = await db.scalar(stmt)
    if not budget:
        raise NotFoundError("Budget not found")
    return budget


async def list_budgets(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    grant_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> tuple[list[Budget], int]:
    filters = [Budget.organization_id == organization_id]
    if grant_id:
        filters.append(Budget.grant_id == grant_id)
    if project_id:
        filters.append(Budget.project_id == project_id)
    if status:
        filters.append(Budget.status == status)
    total = await db.scalar(select(func.count()).select_from(Budget).where(*filters)) or 0
    result = await db.execute(
        select(Budget)
        .where(*filters)
        .order_by(Budget.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def _recalculate_budget_total(db: AsyncSession, budget: Budget) -> None:
    total = await db.scalar(
        select(func.coalesce(func.sum(BudgetLine.amount), 0)).where(
            BudgetLine.budget_id == budget.id
        )
    )
    budget.total_amount = _dec(total)
    await db.flush()


async def create_budget(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    lines: Optional[list[dict]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Budget:
    if data.get("grant_id"):
        await get_grant(db, organization_id, data["grant_id"])
    budget = Budget(
        organization_id=organization_id,
        grant_id=data.get("grant_id"),
        project_id=data.get("project_id"),
        program_id=data.get("program_id"),
        name=data["name"].strip(),
        fiscal_year=data.get("fiscal_year"),
        currency=(data.get("currency") or "USD").upper(),
        status=data.get("status") or "draft",
        notes=data.get("notes"),
        created_by_id=actor_id,
    )
    db.add(budget)
    await db.flush()

    for idx, line in enumerate(lines or []):
        db.add(
            BudgetLine(
                organization_id=organization_id,
                budget_id=budget.id,
                code=line.get("code"),
                category=line["category"],
                description=line.get("description"),
                amount=_dec(line.get("amount")),
                sort_order=line.get("sort_order", idx),
            )
        )
    await db.flush()
    await _recalculate_budget_total(db, budget)

    await write_audit_log(
        db,
        action="budgets.create",
        resource_type="budget",
        resource_id=budget.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created budget {budget.name}",
        changes={"name": budget.name, "lines": len(lines or [])},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_budget(db, organization_id, budget.id, with_lines=True)


async def update_budget(
    db: AsyncSession,
    budget: Budget,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Budget:
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    for key, value in data.items():
        setattr(budget, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="budgets.update",
        resource_type="budget",
        resource_id=budget.id,
        organization_id=budget.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated budget {budget.name}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return budget


async def add_budget_line(
    db: AsyncSession,
    budget: Budget,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BudgetLine:
    line = BudgetLine(
        organization_id=budget.organization_id,
        budget_id=budget.id,
        code=data.get("code"),
        category=data["category"],
        description=data.get("description"),
        amount=_dec(data.get("amount")),
        sort_order=data.get("sort_order", 0),
    )
    db.add(line)
    await db.flush()
    await _recalculate_budget_total(db, budget)
    await write_audit_log(
        db,
        action="budgets.line_create",
        resource_type="budget_line",
        resource_id=line.id,
        organization_id=budget.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Added budget line {line.category}",
        changes={"budget_id": str(budget.id), "amount": str(line.amount)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return line


async def delete_budget(
    db: AsyncSession,
    budget: Budget,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="budgets.delete",
        resource_type="budget",
        resource_id=budget.id,
        organization_id=budget.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted budget {budget.name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(budget)
    await db.flush()


async def list_transactions(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    grant_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    budget_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
) -> tuple[list[FinanceTransaction], int]:
    filters = [FinanceTransaction.organization_id == organization_id]
    if grant_id:
        filters.append(FinanceTransaction.grant_id == grant_id)
    if project_id:
        filters.append(FinanceTransaction.project_id == project_id)
    if budget_id:
        filters.append(FinanceTransaction.budget_id == budget_id)
    if transaction_type:
        filters.append(FinanceTransaction.transaction_type == transaction_type)
    total = (
        await db.scalar(
            select(func.count()).select_from(FinanceTransaction).where(*filters)
        )
        or 0
    )
    result = await db.execute(
        select(FinanceTransaction)
        .where(*filters)
        .order_by(FinanceTransaction.transaction_date.desc(), FinanceTransaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_transaction(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> FinanceTransaction:
    if data.get("grant_id"):
        await get_grant(db, organization_id, data["grant_id"])
    if data.get("budget_id"):
        await get_budget(db, organization_id, data["budget_id"])

    txn = FinanceTransaction(
        organization_id=organization_id,
        grant_id=data.get("grant_id"),
        project_id=data.get("project_id"),
        budget_id=data.get("budget_id"),
        budget_line_id=data.get("budget_line_id"),
        transaction_type=data["transaction_type"],
        status=data.get("status") or "posted",
        amount=_dec(data["amount"]),
        currency=(data.get("currency") or "USD").upper(),
        transaction_date=data["transaction_date"],
        description=data.get("description"),
        reference=data.get("reference"),
        category=data.get("category"),
        created_by_id=actor_id,
    )
    db.add(txn)
    await db.flush()

    # Keep grant amount_received in sync for income postings
    if (
        txn.grant_id
        and txn.transaction_type == "income"
        and txn.status == "posted"
    ):
        grant = await get_grant(db, organization_id, txn.grant_id)
        grant.amount_received = _dec(grant.amount_received) + txn.amount
        await db.flush()

    await write_audit_log(
        db,
        action="finance.create",
        resource_type="finance_transaction",
        resource_id=txn.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Posted {txn.transaction_type} of {txn.amount} {txn.currency}",
        changes={
            "transaction_type": txn.transaction_type,
            "amount": str(txn.amount),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return txn


async def update_transaction(
    db: AsyncSession,
    txn: FinanceTransaction,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> FinanceTransaction:
    if "amount" in data:
        data["amount"] = _dec(data["amount"])
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    for key, value in data.items():
        setattr(txn, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="finance.update",
        resource_type="finance_transaction",
        resource_id=txn.id,
        organization_id=txn.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description="Updated finance transaction",
        changes={k: str(v) for k, v in data.items()},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return txn


async def get_transaction(
    db: AsyncSession, organization_id: UUID, transaction_id: UUID
) -> FinanceTransaction:
    txn = await db.scalar(
        select(FinanceTransaction).where(
            FinanceTransaction.id == transaction_id,
            FinanceTransaction.organization_id == organization_id,
        )
    )
    if not txn:
        raise NotFoundError("Transaction not found")
    return txn


async def phase3_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int | str]:
    donors = await db.scalar(
        select(func.count()).select_from(Donor).where(Donor.organization_id == organization_id)
    )
    grants = await db.scalar(
        select(func.count()).select_from(Grant).where(Grant.organization_id == organization_id)
    )
    active_grants = await db.scalar(
        select(func.count())
        .select_from(Grant)
        .where(
            Grant.organization_id == organization_id,
            Grant.status.in_(["awarded", "active"]),
        )
    )
    budgets = await db.scalar(
        select(func.count()).select_from(Budget).where(Budget.organization_id == organization_id)
    )
    awarded = await db.scalar(
        select(func.coalesce(func.sum(Grant.amount_awarded), 0)).where(
            Grant.organization_id == organization_id
        )
    )
    received = await db.scalar(
        select(func.coalesce(func.sum(Grant.amount_received), 0)).where(
            Grant.organization_id == organization_id
        )
    )
    expenses = await db.scalar(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.organization_id == organization_id,
            FinanceTransaction.transaction_type == "expense",
            FinanceTransaction.status == "posted",
        )
    )
    return {
        "donors_count": donors or 0,
        "grants_count": grants or 0,
        "active_grants_count": active_grants or 0,
        "budgets_count": budgets or 0,
        "grants_awarded_total": str(_dec(awarded)),
        "grants_received_total": str(_dec(received)),
        "expenses_total": str(_dec(expenses)),
    }
