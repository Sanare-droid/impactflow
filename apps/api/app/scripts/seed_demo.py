"""
Seed a demo organization with sample portfolio data.

Usage (inside API container or venv):
  python -m app.scripts.seed_demo

Optional env:
  DEMO_ORG_SLUG=demo
  DEMO_ADMIN_EMAIL=demo@example.com
  DEMO_ADMIN_PASSWORD=DemoPass12345!
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.beneficiary import Beneficiary
from app.models.community import Community
from app.models.donor import Donor
from app.models.grant import Grant
from app.models.indicator import Indicator
from app.models.knowledge import KnowledgeDocument
from app.models.logframe import Logframe
from app.models.organization import Organization
from app.models.program import Program
from app.models.project import Project
from app.models.theory_of_change import TheoryOfChange
from app.models.user import User
from app.services.auth import (
    create_org_system_roles,
    ensure_permission_catalog,
    slugify,
)
from app.services.platform import ensure_marketplace_catalog


async def run() -> None:
    slug = os.getenv("DEMO_ORG_SLUG", "demo")
    email = os.getenv("DEMO_ADMIN_EMAIL", "demo@example.com").lower()
    password = os.getenv("DEMO_ADMIN_PASSWORD", "DemoPass12345!")

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Organization).where(Organization.slug == slug))
        if existing:
            print(f"Demo org '{slug}' already exists ({existing.id}). Skipping.")
            return

        perms = await ensure_permission_catalog(db)
        org = Organization(
            name="ImpactFlow Demo Org",
            slug=slugify(slug),
            organization_type="ngo",
            country_code="KE",
            description="Seeded demo workspace for pilots and sales.",
            is_verified=True,
        )
        db.add(org)
        await db.flush()
        roles = await create_org_system_roles(db, org.id, perms)
        admin_role = roles["org_admin"]

        user = User(
            email=email,
            hashed_password=hash_password(password),
            first_name="Demo",
            last_name="Admin",
            primary_organization_id=org.id,
            email_verified=True,
            must_change_password=False,
            password_changed_at=utcnow(),
        )
        db.add(user)
        await db.flush()

        from app.models.membership import OrganizationMembership

        db.add(
            OrganizationMembership(
                organization_id=org.id,
                user_id=user.id,
                role_id=admin_role.id,
                status="active",
                joined_at=utcnow(),
            )
        )

        program = Program(
            organization_id=org.id,
            name="Resilient Communities",
            code="PRG-DEMO-RC",
            status="active",
            goal="Improve household resilience through livelihoods and health.",
            manager_id=user.id,
        )
        db.add(program)
        await db.flush()

        project = Project(
            organization_id=org.id,
            program_id=program.id,
            name="Nairobi Livelihoods Pilot",
            code="PRJ-DEMO-NLP",
            status="active",
            description="Demo field project for beneficiary and MEAL workflows.",
        )
        db.add(project)
        await db.flush()

        donor = Donor(
            organization_id=org.id,
            name="Demo Foundation",
            code="DNR-DEMO",
            donor_type="foundation",
            status="active",
        )
        db.add(donor)
        await db.flush()

        grant = Grant(
            organization_id=org.id,
            donor_id=donor.id,
            program_id=program.id,
            project_id=project.id,
            name="Demo Resilience Grant",
            code="GRN-DEMO",
            status="active",
            currency="USD",
            amount_awarded=Decimal("250000"),
            amount_received=Decimal("100000"),
        )
        db.add(grant)

        toc = TheoryOfChange(
            organization_id=org.id,
            program_id=program.id,
            name="Demo Theory of Change",
            code="TOC-DEMO",
            status="active",
            goal_statement="Households sustain livelihoods and access essential services.",
        )
        db.add(toc)
        await db.flush()

        logframe = Logframe(
            organization_id=org.id,
            theory_of_change_id=toc.id,
            program_id=program.id,
            name="Demo Logframe",
            code="LF-DEMO",
            status="active",
        )
        db.add(logframe)
        await db.flush()

        indicator = Indicator(
            organization_id=org.id,
            program_id=program.id,
            project_id=project.id,
            name="Households with diversified income",
            code="IND-DEMO-01",
            status="active",
            level="outcome",
            unit="households",
        )
        db.add(indicator)

        community = Community(
            organization_id=org.id,
            name="Demo Ward",
            code="COM-DEMO",
            status="active",
            country_code="KE",
        )
        db.add(community)
        await db.flush()

        beneficiary = Beneficiary(
            organization_id=org.id,
            community_id=community.id,
            first_name="Amina",
            last_name="Otieno",
            code="BEN-DEMO-001",
            status="active",
            sex="female",
            consent_data_use=True,
        )
        db.add(beneficiary)

        db.add(
            KnowledgeDocument(
                organization_id=org.id,
                name="Indicator verification SOP",
                code="KB-DEMO-SOP",
                category="sop",
                status="published",
                summary="How field officers verify monitoring results.",
                content=(
                    "Verify source documents before approving monitoring results. "
                    "Link evidence photos and note GPS when available."
                ),
                tags=["meal", "field"],
                created_by_id=user.id,
            )
        )

        await ensure_marketplace_catalog(db)
        await db.commit()

        print("Demo seed complete.")
        print(f"  Org slug:  {org.slug}")
        print(f"  Admin:     {email}")
        print(f"  Password:  {password}")
        print("  Sign in at the web app with this account.")


if __name__ == "__main__":
    asyncio.run(run())
