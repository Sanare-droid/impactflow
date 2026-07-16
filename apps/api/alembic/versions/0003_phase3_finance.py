"""phase3 donors grants budgets finance

Revision ID: 0003_phase3
Revises: 0002_phase2
Create Date: 2026-07-16

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase3"
down_revision: Union[str, None] = "0002_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "donors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("donor_type", sa.String(64), nullable=False, server_default="foundation"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("country_code", sa.String(2)),
        sa.Column("contact_name", sa.String(200)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(64)),
        sa.Column("website", sa.String(512)),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "code", name="uq_donors_org_code"),
    )
    op.create_index("ix_donors_organization_id", "donors", ["organization_id"])
    op.create_index("ix_donors_code", "donors", ["code"])
    op.create_index("ix_donors_status", "donors", ["status"])

    op.create_table(
        "grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("donor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="pipeline"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("amount_awarded", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("amount_received", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("agreement_reference", sa.String(128)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["donor_id"], ["donors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "code", name="uq_grants_org_code"),
    )
    op.create_index("ix_grants_organization_id", "grants", ["organization_id"])
    op.create_index("ix_grants_donor_id", "grants", ["donor_id"])
    op.create_index("ix_grants_program_id", "grants", ["program_id"])
    op.create_index("ix_grants_project_id", "grants", ["project_id"])
    op.create_index("ix_grants_code", "grants", ["code"])
    op.create_index("ix_grants_status", "grants", ["status"])

    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("program_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("fiscal_year", sa.Integer()),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grant_id"], ["grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_budgets_organization_id", "budgets", ["organization_id"])
    op.create_index("ix_budgets_grant_id", "budgets", ["grant_id"])
    op.create_index("ix_budgets_project_id", "budgets", ["project_id"])
    op.create_index("ix_budgets_program_id", "budgets", ["program_id"])
    op.create_index("ix_budgets_status", "budgets", ["status"])

    op.create_table(
        "budget_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64)),
        sa.Column("category", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_budget_lines_organization_id", "budget_lines", ["organization_id"])
    op.create_index("ix_budget_lines_budget_id", "budget_lines", ["budget_id"])

    op.create_table(
        "finance_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True)),
        sa.Column("budget_line_id", postgresql.UUID(as_uuid=True)),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="posted"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("reference", sa.String(128)),
        sa.Column("category", sa.String(128)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grant_id"], ["grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["budget_line_id"], ["budget_lines.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_finance_transactions_organization_id", "finance_transactions", ["organization_id"])
    op.create_index("ix_finance_transactions_grant_id", "finance_transactions", ["grant_id"])
    op.create_index("ix_finance_transactions_project_id", "finance_transactions", ["project_id"])
    op.create_index("ix_finance_transactions_budget_id", "finance_transactions", ["budget_id"])
    op.create_index("ix_finance_transactions_budget_line_id", "finance_transactions", ["budget_line_id"])
    op.create_index("ix_finance_transactions_transaction_type", "finance_transactions", ["transaction_type"])
    op.create_index("ix_finance_transactions_status", "finance_transactions", ["status"])


def downgrade() -> None:
    op.drop_table("finance_transactions")
    op.drop_table("budget_lines")
    op.drop_table("budgets")
    op.drop_table("grants")
    op.drop_table("donors")
