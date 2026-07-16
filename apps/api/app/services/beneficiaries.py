from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.beneficiary import Beneficiary, BeneficiaryMembership
from app.models.community import Community
from app.models.household import Household
from app.models.program import Program
from app.models.project import Project
from app.services.audit import write_audit_log
from app.services.programs import make_code, _ensure_unique_code


def _dec(value: Optional[Decimal | float | int | str]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def _full_name(first: str, last: str, middle: Optional[str] = None) -> str:
    parts = [first.strip(), (middle or "").strip(), last.strip()]
    return " ".join(p for p in parts if p)


async def _assert_program(db: AsyncSession, organization_id: UUID, program_id: UUID) -> None:
    exists = await db.scalar(
        select(Program.id).where(Program.id == program_id, Program.organization_id == organization_id)
    )
    if not exists:
        raise NotFoundError("Program not found")


async def _assert_project(db: AsyncSession, organization_id: UUID, project_id: UUID) -> None:
    exists = await db.scalar(
        select(Project.id).where(Project.id == project_id, Project.organization_id == organization_id)
    )
    if not exists:
        raise NotFoundError("Project not found")


# -------- Communities --------


async def get_community(db: AsyncSession, organization_id: UUID, community_id: UUID) -> Community:
    community = await db.scalar(
        select(Community).where(
            Community.id == community_id, Community.organization_id == organization_id
        )
    )
    if not community:
        raise NotFoundError("Community not found")
    return community


async def list_communities(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Community], int]:
    filters = [Community.organization_id == organization_id]
    if status:
        filters.append(Community.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(Community.name.ilike(like), Community.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Community).where(*filters)) or 0
    result = await db.execute(
        select(Community)
        .where(*filters)
        .order_by(Community.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_community(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Community:
    if data.get("parent_id"):
        await get_community(db, organization_id, data["parent_id"])
    code = await _ensure_unique_code(
        db,
        model=Community,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="COM-"),
    )
    community = Community(
        organization_id=organization_id,
        parent_id=data.get("parent_id"),
        name=data["name"].strip(),
        code=code,
        community_type=data.get("community_type") or "village",
        status=data.get("status") or "active",
        country_code=(data.get("country_code") or "").upper() or None,
        region=data.get("region"),
        district=data.get("district"),
        latitude=_dec(data.get("latitude")),
        longitude=_dec(data.get("longitude")),
        population_estimate=data.get("population_estimate"),
        notes=data.get("notes"),
        created_by_id=actor_id,
    )
    db.add(community)
    await db.flush()
    await write_audit_log(
        db,
        action="communities.create",
        resource_type="community",
        resource_id=community.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created community {community.code}",
        changes={"name": community.name, "code": community.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return community


async def update_community(
    db: AsyncSession,
    community: Community,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Community:
    if data.get("parent_id"):
        await get_community(db, community.organization_id, data["parent_id"])
    if "latitude" in data:
        data["latitude"] = _dec(data["latitude"])
    if "longitude" in data:
        data["longitude"] = _dec(data["longitude"])
    if "country_code" in data and data["country_code"]:
        data["country_code"] = data["country_code"].upper()
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="COM-")
        if new_code != community.code:
            data["code"] = await _ensure_unique_code(
                db, model=Community, organization_id=community.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(community, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="communities.update",
        resource_type="community",
        resource_id=community.id,
        organization_id=community.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated community {community.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return community


async def delete_community(
    db: AsyncSession,
    community: Community,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="communities.delete",
        resource_type="community",
        resource_id=community.id,
        organization_id=community.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted community {community.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(community)
    await db.flush()


# -------- Households --------


async def get_household(db: AsyncSession, organization_id: UUID, household_id: UUID) -> Household:
    household = await db.scalar(
        select(Household)
        .options(selectinload(Household.members))
        .where(Household.id == household_id, Household.organization_id == organization_id)
    )
    if not household:
        raise NotFoundError("Household not found")
    return household


async def list_households(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    community_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Household], int]:
    filters = [Household.organization_id == organization_id]
    if community_id:
        filters.append(Household.community_id == community_id)
    if status:
        filters.append(Household.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append(or_(Household.name.ilike(like), Household.code.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(Household).where(*filters)) or 0
    result = await db.execute(
        select(Household)
        .where(*filters)
        .order_by(Household.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_household(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Household:
    if data.get("community_id"):
        await get_community(db, organization_id, data["community_id"])
    code = await _ensure_unique_code(
        db,
        model=Household,
        organization_id=organization_id,
        code=make_code(data.get("code") or data["name"], prefix="HH-"),
    )
    household = Household(
        organization_id=organization_id,
        community_id=data.get("community_id"),
        name=data["name"].strip(),
        code=code,
        status=data.get("status") or "active",
        address=data.get("address"),
        latitude=_dec(data.get("latitude")),
        longitude=_dec(data.get("longitude")),
        household_size=data.get("household_size"),
        poverty_status=data.get("poverty_status"),
        notes=data.get("notes"),
        created_by_id=actor_id,
    )
    db.add(household)
    await db.flush()
    await write_audit_log(
        db,
        action="households.create",
        resource_type="household",
        resource_id=household.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Created household {household.code}",
        changes={"name": household.name, "code": household.code},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return household


async def update_household(
    db: AsyncSession,
    household: Household,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Household:
    if data.get("community_id"):
        await get_community(db, household.organization_id, data["community_id"])
    if "latitude" in data:
        data["latitude"] = _dec(data["latitude"])
    if "longitude" in data:
        data["longitude"] = _dec(data["longitude"])
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="HH-")
        if new_code != household.code:
            data["code"] = await _ensure_unique_code(
                db, model=Household, organization_id=household.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(household, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="households.update",
        resource_type="household",
        resource_id=household.id,
        organization_id=household.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated household {household.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return household


async def delete_household(
    db: AsyncSession,
    household: Household,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="households.delete",
        resource_type="household",
        resource_id=household.id,
        organization_id=household.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted household {household.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(household)
    await db.flush()


# -------- Beneficiaries --------


async def get_beneficiary(
    db: AsyncSession, organization_id: UUID, beneficiary_id: UUID
) -> Beneficiary:
    beneficiary = await db.scalar(
        select(Beneficiary)
        .options(selectinload(Beneficiary.memberships))
        .where(Beneficiary.id == beneficiary_id, Beneficiary.organization_id == organization_id)
    )
    if not beneficiary:
        raise NotFoundError("Beneficiary not found")
    return beneficiary


async def list_beneficiaries(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    household_id: Optional[UUID] = None,
    community_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Beneficiary], int]:
    filters = [Beneficiary.organization_id == organization_id]
    if household_id:
        filters.append(Beneficiary.household_id == household_id)
    if community_id:
        filters.append(Beneficiary.community_id == community_id)
    if status:
        filters.append(Beneficiary.status == status)
    if search:
        like = f"%{search.strip()}%"
        filters.append(
            or_(
                Beneficiary.first_name.ilike(like),
                Beneficiary.last_name.ilike(like),
                Beneficiary.code.ilike(like),
                Beneficiary.national_id.ilike(like),
                Beneficiary.phone.ilike(like),
            )
        )
    total = await db.scalar(select(func.count()).select_from(Beneficiary).where(*filters)) or 0
    result = await db.execute(
        select(Beneficiary)
        .options(selectinload(Beneficiary.memberships))
        .where(*filters)
        .order_by(Beneficiary.last_name.asc(), Beneficiary.first_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all()), total


async def create_beneficiary(
    db: AsyncSession,
    *,
    organization_id: UUID,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Beneficiary:
    if data.get("household_id"):
        await get_household(db, organization_id, data["household_id"])
    if data.get("community_id"):
        await get_community(db, organization_id, data["community_id"])
    memberships_data = data.pop("memberships", None) or []
    display = _full_name(data["first_name"], data["last_name"], data.get("middle_name"))
    code = await _ensure_unique_code(
        db,
        model=Beneficiary,
        organization_id=organization_id,
        code=make_code(data.get("code") or display, prefix="BEN-"),
    )
    beneficiary = Beneficiary(
        organization_id=organization_id,
        household_id=data.get("household_id"),
        community_id=data.get("community_id"),
        code=code,
        first_name=data["first_name"].strip(),
        last_name=data["last_name"].strip(),
        middle_name=(data.get("middle_name") or None),
        sex=data.get("sex"),
        date_of_birth=data.get("date_of_birth"),
        national_id=data.get("national_id"),
        phone=data.get("phone"),
        email=data.get("email"),
        status=data.get("status") or "active",
        registration_date=data.get("registration_date") or date.today(),
        consent_data_use=bool(data.get("consent_data_use", False)),
        consent_photo=bool(data.get("consent_photo", False)),
        is_household_head=bool(data.get("is_household_head", False)),
        vulnerability_tags=data.get("vulnerability_tags") or [],
        latitude=_dec(data.get("latitude")),
        longitude=_dec(data.get("longitude")),
        notes=data.get("notes"),
        photo_url=data.get("photo_url"),
        created_by_id=actor_id,
    )
    db.add(beneficiary)
    await db.flush()
    for membership in memberships_data:
        if membership.get("program_id"):
            await _assert_program(db, organization_id, membership["program_id"])
        if membership.get("project_id"):
            await _assert_project(db, organization_id, membership["project_id"])
        db.add(
            BeneficiaryMembership(
                organization_id=organization_id,
                beneficiary_id=beneficiary.id,
                program_id=membership.get("program_id"),
                project_id=membership.get("project_id"),
                activity_id=membership.get("activity_id"),
                membership_role=membership.get("membership_role") or "participant",
                status=membership.get("status") or "enrolled",
                start_date=membership.get("start_date") or date.today(),
                end_date=membership.get("end_date"),
                exit_reason=membership.get("exit_reason"),
                notes=membership.get("notes"),
                created_by_id=actor_id,
            )
        )
    await db.flush()
    await write_audit_log(
        db,
        action="beneficiaries.create",
        resource_type="beneficiary",
        resource_id=beneficiary.id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Registered beneficiary {beneficiary.code}",
        changes={"code": beneficiary.code, "name": display},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_beneficiary(db, organization_id, beneficiary.id)


async def update_beneficiary(
    db: AsyncSession,
    beneficiary: Beneficiary,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Beneficiary:
    if data.get("household_id"):
        await get_household(db, beneficiary.organization_id, data["household_id"])
    if data.get("community_id"):
        await get_community(db, beneficiary.organization_id, data["community_id"])
    if "latitude" in data:
        data["latitude"] = _dec(data["latitude"])
    if "longitude" in data:
        data["longitude"] = _dec(data["longitude"])
    if "code" in data and data["code"]:
        new_code = make_code(data["code"], prefix="BEN-")
        if new_code != beneficiary.code:
            data["code"] = await _ensure_unique_code(
                db, model=Beneficiary, organization_id=beneficiary.organization_id, code=new_code
            )
    for key, value in data.items():
        setattr(beneficiary, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="beneficiaries.update",
        resource_type="beneficiary",
        resource_id=beneficiary.id,
        organization_id=beneficiary.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Updated beneficiary {beneficiary.code}",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return await get_beneficiary(db, beneficiary.organization_id, beneficiary.id)


async def delete_beneficiary(
    db: AsyncSession,
    beneficiary: Beneficiary,
    *,
    actor_id: UUID,
    actor_email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    await write_audit_log(
        db,
        action="beneficiaries.delete",
        resource_type="beneficiary",
        resource_id=beneficiary.id,
        organization_id=beneficiary.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Deleted beneficiary {beneficiary.code}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.delete(beneficiary)
    await db.flush()


async def add_membership(
    db: AsyncSession,
    beneficiary: Beneficiary,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BeneficiaryMembership:
    if data.get("program_id"):
        await _assert_program(db, beneficiary.organization_id, data["program_id"])
    if data.get("project_id"):
        await _assert_project(db, beneficiary.organization_id, data["project_id"])
    membership = BeneficiaryMembership(
        organization_id=beneficiary.organization_id,
        beneficiary_id=beneficiary.id,
        program_id=data.get("program_id"),
        project_id=data.get("project_id"),
        activity_id=data.get("activity_id"),
        membership_role=data.get("membership_role") or "participant",
        status=data.get("status") or "enrolled",
        start_date=data.get("start_date") or date.today(),
        end_date=data.get("end_date"),
        exit_reason=data.get("exit_reason"),
        notes=data.get("notes"),
        created_by_id=actor_id,
    )
    db.add(membership)
    await db.flush()
    await write_audit_log(
        db,
        action="beneficiaries.memberships.create",
        resource_type="beneficiary_membership",
        resource_id=membership.id,
        organization_id=beneficiary.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description=f"Enrolled {beneficiary.code} in program/project",
        changes={
            "program_id": str(membership.program_id) if membership.program_id else None,
            "project_id": str(membership.project_id) if membership.project_id else None,
            "status": membership.status,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return membership


async def update_membership(
    db: AsyncSession,
    membership: BeneficiaryMembership,
    *,
    actor_id: UUID,
    actor_email: str,
    data: dict,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BeneficiaryMembership:
    for key, value in data.items():
        setattr(membership, key, value)
    await db.flush()
    await write_audit_log(
        db,
        action="beneficiaries.memberships.update",
        resource_type="beneficiary_membership",
        resource_id=membership.id,
        organization_id=membership.organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        description="Updated beneficiary membership",
        changes=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return membership


async def get_membership(
    db: AsyncSession, organization_id: UUID, membership_id: UUID
) -> BeneficiaryMembership:
    membership = await db.scalar(
        select(BeneficiaryMembership).where(
            BeneficiaryMembership.id == membership_id,
            BeneficiaryMembership.organization_id == organization_id,
        )
    )
    if not membership:
        raise NotFoundError("Membership not found")
    return membership


async def list_memberships(
    db: AsyncSession,
    organization_id: UUID,
    *,
    page: int,
    page_size: int,
    beneficiary_id: Optional[UUID] = None,
    program_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> tuple[list[BeneficiaryMembership], int]:
    filters = [BeneficiaryMembership.organization_id == organization_id]
    if beneficiary_id:
        filters.append(BeneficiaryMembership.beneficiary_id == beneficiary_id)
    if program_id:
        filters.append(BeneficiaryMembership.program_id == program_id)
    if project_id:
        filters.append(BeneficiaryMembership.project_id == project_id)
    if status:
        filters.append(BeneficiaryMembership.status == status)
    total = (
        await db.scalar(select(func.count()).select_from(BeneficiaryMembership).where(*filters))
        or 0
    )
    result = await db.execute(
        select(BeneficiaryMembership)
        .where(*filters)
        .order_by(BeneficiaryMembership.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def phase5_counts(db: AsyncSession, organization_id: UUID) -> dict[str, int]:
    communities = await db.scalar(
        select(func.count())
        .select_from(Community)
        .where(Community.organization_id == organization_id)
    )
    households = await db.scalar(
        select(func.count())
        .select_from(Household)
        .where(Household.organization_id == organization_id)
    )
    beneficiaries = await db.scalar(
        select(func.count())
        .select_from(Beneficiary)
        .where(Beneficiary.organization_id == organization_id)
    )
    active_beneficiaries = await db.scalar(
        select(func.count())
        .select_from(Beneficiary)
        .where(Beneficiary.organization_id == organization_id, Beneficiary.status == "active")
    )
    memberships = await db.scalar(
        select(func.count())
        .select_from(BeneficiaryMembership)
        .where(BeneficiaryMembership.organization_id == organization_id)
    )
    return {
        "communities_count": communities or 0,
        "households_count": households or 0,
        "beneficiaries_count": beneficiaries or 0,
        "active_beneficiaries_count": active_beneficiaries or 0,
        "beneficiary_memberships_count": memberships or 0,
    }
