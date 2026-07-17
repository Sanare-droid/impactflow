from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MessageResponse(BaseModel):
    message: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta


# -------- Auth --------


class RegisterOrganizationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    organization_slug: Optional[str] = Field(default=None, max_length=100)
    organization_type: str = Field(default="ngo", max_length=64)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < settings.password_min_length:
            raise ValueError(
                f"Password must be at least {settings.password_min_length} characters"
            )
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain an uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must contain a lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain a digit")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    organization_slug: Optional[str] = None
    mfa_code: Optional[str] = Field(default=None, min_length=6, max_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    mfa_required: bool = False
    user: "UserBrief"
    organization_id: Optional[UUID] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MFAEnableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


# -------- Users / Orgs --------


class UserBrief(ORMModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    mfa_enabled: bool
    must_change_password: bool = False
    primary_organization_id: Optional[UUID] = None


class UserResponse(UserBrief):
    phone: Optional[str] = None
    job_title: Optional[str] = None
    locale: str
    timezone: str
    email_verified: bool
    is_superuser: bool
    is_platform_admin: bool = False
    last_login_at: Optional[Any] = None
    created_at: Any


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return RegisterOrganizationRequest.validate_password(value)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_reset_password(cls, value: str) -> str:
        return RegisterOrganizationRequest.validate_password(value)


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    display_name: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=64)
    job_title: Optional[str] = Field(default=None, max_length=150)
    locale: Optional[str] = Field(default=None, max_length=16)
    timezone: Optional[str] = Field(default=None, max_length=64)
    avatar_url: Optional[str] = Field(default=None, max_length=512)


class InviteUserRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role_id: UUID
    job_title: Optional[str] = None
    send_invite: bool = True


class UpdateMembershipRoleRequest(BaseModel):
    role_id: UUID


class OrganizationResponse(ORMModel):
    id: UUID
    name: str
    slug: str
    legal_name: Optional[str] = None
    organization_type: str
    country_code: Optional[str] = None
    timezone: str
    locale: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    is_verified: bool
    settings: dict
    created_at: Any


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    organization_type: Optional[str] = Field(default=None, max_length=64)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    timezone: Optional[str] = Field(default=None, max_length=64)
    locale: Optional[str] = Field(default=None, max_length=16)
    logo_url: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[dict] = None


class RoleResponse(ORMModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    is_system: bool
    is_default: bool
    organization_id: Optional[UUID] = None
    permissions: list[str] = []


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)
    is_default: bool = False


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    is_default: Optional[bool] = None


class PermissionResponse(ORMModel):
    id: UUID
    code: str
    module: str
    action: str
    description: Optional[str] = None


class MembershipResponse(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role_id: UUID
    status: str
    user: Optional[UserBrief] = None
    role: Optional[RoleResponse] = None


class DashboardStatsResponse(BaseModel):
    users_count: int
    active_memberships: int
    roles_count: int
    recent_audit_events: int
    organization: OrganizationResponse
    programs_count: int = 0
    projects_count: int = 0
    activities_count: int = 0
    tasks_count: int = 0
    open_tasks_count: int = 0
    donors_count: int = 0
    grants_count: int = 0
    active_grants_count: int = 0
    budgets_count: int = 0
    grants_awarded_total: str = "0"
    grants_received_total: str = "0"
    expenses_total: str = "0"
    theories_of_change_count: int = 0
    logframes_count: int = 0
    indicators_count: int = 0
    active_indicators_count: int = 0
    monitoring_results_count: int = 0
    evaluations_count: int = 0
    communities_count: int = 0
    households_count: int = 0
    beneficiaries_count: int = 0
    active_beneficiaries_count: int = 0
    beneficiary_memberships_count: int = 0
    reports_count: int = 0
    published_reports_count: int = 0
    saved_dashboards_count: int = 0
    map_layers_count: int = 0
    map_features_count: int = 0
    evidence_count: int = 0
    verified_evidence_count: int = 0
    ai_conversations_count: int = 0
    ai_predictions_count: int = 0
    open_predictions_count: int = 0
    ai_narratives_count: int = 0
    knowledge_documents_count: int = 0
    marketplace_installs_count: int = 0
    integrations_count: int = 0
    api_keys_count: int = 0
    branding_enabled_count: int = 0
    notifications_count: int = 0
    unread_notifications_count: int = 0
    webhook_pending_count: int = 0
    webhook_failed_count: int = 0
    surveys_count: int = 0
    published_surveys_count: int = 0
    survey_responses_count: int = 0


class AuditLogResponse(ORMModel):
    id: UUID
    organization_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    description: Optional[str] = None
    status: str
    changes: dict
    created_at: Any


# -------- Phase 2: Programs / Projects / Activities / Work Plans / Tasks --------


class ProgramCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="draft", max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    manager_id: Optional[UUID] = None
    goal: Optional[str] = None
    tags: Optional[list[str]] = None


class ProgramUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    manager_id: Optional[UUID] = None
    goal: Optional[str] = None
    tags: Optional[list[str]] = None


class ProgramResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    manager_id: Optional[UUID] = None
    goal: Optional[str] = None
    tags: list = []
    created_at: Any
    updated_at: Any


class ProjectCreateRequest(BaseModel):
    program_id: UUID
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="planning", max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    location: Optional[str] = None
    manager_id: Optional[UUID] = None
    priority: str = Field(default="medium", max_length=16)
    tags: Optional[list[str]] = None


class ProjectUpdateRequest(BaseModel):
    program_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    location: Optional[str] = None
    manager_id: Optional[UUID] = None
    priority: Optional[str] = Field(default=None, max_length=16)
    tags: Optional[list[str]] = None


class ProjectResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    country_code: Optional[str] = None
    location: Optional[str] = None
    manager_id: Optional[UUID] = None
    priority: str
    tags: list = []
    created_at: Any
    updated_at: Any


class ActivityCreateRequest(BaseModel):
    project_id: UUID
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="planned", max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sort_order: int = 0
    owner_id: Optional[UUID] = None
    location: Optional[str] = None


class ActivityUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sort_order: Optional[int] = None
    owner_id: Optional[UUID] = None
    location: Optional[str] = None


class ActivityResponse(ORMModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sort_order: int
    owner_id: Optional[UUID] = None
    location: Optional[str] = None
    created_at: Any
    updated_at: Any


class WorkPlanCreateRequest(BaseModel):
    project_id: UUID
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    status: str = Field(default="draft", max_length=32)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    fiscal_year: Optional[int] = None
    period_label: Optional[str] = Field(default=None, max_length=64)


class WorkPlanUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    fiscal_year: Optional[int] = None
    period_label: Optional[str] = Field(default=None, max_length=64)


class WorkPlanResponse(ORMModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    description: Optional[str] = None
    status: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    fiscal_year: Optional[int] = None
    period_label: Optional[str] = None
    created_at: Any
    updated_at: Any


class TaskCreateRequest(BaseModel):
    project_id: UUID
    title: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    status: str = Field(default="todo", max_length=32)
    priority: str = Field(default="medium", max_length=16)
    activity_id: Optional[UUID] = None
    work_plan_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    priority: Optional[str] = Field(default=None, max_length=16)
    activity_id: Optional[UUID] = None
    work_plan_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None


class TaskResponse(ORMModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    activity_id: Optional[UUID] = None
    work_plan_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None
    completed_at: Optional[Any] = None
    created_at: Any
    updated_at: Any


# -------- Phase 3: Donors / Grants / Budgets / Finance --------


class DonorCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    donor_type: str = Field(default="foundation", max_length=64)
    status: str = Field(default="active", max_length=32)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None


class DonorUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    donor_type: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None


class DonorResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    donor_type: str
    status: str
    country_code: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    created_at: Any
    updated_at: Any


class GrantCreateRequest(BaseModel):
    donor_id: UUID
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="pipeline", max_length=32)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    amount_awarded: float = 0
    amount_received: float = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    agreement_reference: Optional[str] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class GrantUpdateRequest(BaseModel):
    donor_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    amount_awarded: Optional[float] = None
    amount_received: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    agreement_reference: Optional[str] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class GrantResponse(ORMModel):
    id: UUID
    organization_id: UUID
    donor_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    name: str
    code: str
    description: Optional[str] = None
    status: str
    currency: str
    amount_awarded: Any
    amount_received: Any
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    agreement_reference: Optional[str] = None
    created_at: Any
    updated_at: Any


class BudgetLineCreateRequest(BaseModel):
    category: str = Field(min_length=1, max_length=128)
    code: Optional[str] = None
    description: Optional[str] = None
    amount: float = 0
    sort_order: int = 0


class BudgetLineResponse(ORMModel):
    id: UUID
    organization_id: UUID
    budget_id: UUID
    code: Optional[str] = None
    category: str
    description: Optional[str] = None
    amount: Any
    sort_order: int
    created_at: Any
    updated_at: Any


class BudgetCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    grant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    fiscal_year: Optional[int] = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: str = Field(default="draft", max_length=32)
    notes: Optional[str] = None
    lines: Optional[list[BudgetLineCreateRequest]] = None


class BudgetUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    grant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    fiscal_year: Optional[int] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    status: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = None


class BudgetResponse(ORMModel):
    id: UUID
    organization_id: UUID
    grant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    name: str
    fiscal_year: Optional[int] = None
    currency: str
    status: str
    total_amount: Any
    notes: Optional[str] = None
    lines: list[BudgetLineResponse] = []
    created_at: Any
    updated_at: Any


class FinanceTransactionCreateRequest(BaseModel):
    transaction_type: str = Field(min_length=2, max_length=32)
    amount: float
    transaction_date: date
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: str = Field(default="posted", max_length=32)
    description: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[str] = None
    grant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    budget_line_id: Optional[UUID] = None


class FinanceTransactionUpdateRequest(BaseModel):
    transaction_type: Optional[str] = Field(default=None, max_length=32)
    amount: Optional[float] = None
    transaction_date: Optional[date] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    status: Optional[str] = Field(default=None, max_length=32)
    description: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[str] = None
    grant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    budget_line_id: Optional[UUID] = None


class FinanceTransactionResponse(ORMModel):
    id: UUID
    organization_id: UUID
    grant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    budget_id: Optional[UUID] = None
    budget_line_id: Optional[UUID] = None
    transaction_type: str
    status: str
    amount: Any
    currency: str
    transaction_date: date
    description: Optional[str] = None
    reference: Optional[str] = None
    category: Optional[str] = None
    created_at: Any
    updated_at: Any


# -------- Phase 4: MEAL --------


class TheoryOfChangeCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    status: str = Field(default="draft", max_length=32)
    goal_statement: Optional[str] = None
    problem_statement: Optional[str] = None
    assumptions: Optional[str] = None
    success_criteria: Optional[str] = None
    pathways: Optional[list] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class TheoryOfChangeUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    goal_statement: Optional[str] = None
    problem_statement: Optional[str] = None
    assumptions: Optional[str] = None
    success_criteria: Optional[str] = None
    pathways: Optional[list] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class TheoryOfChangeResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    name: str
    code: str
    status: str
    goal_statement: Optional[str] = None
    problem_statement: Optional[str] = None
    assumptions: Optional[str] = None
    success_criteria: Optional[str] = None
    pathways: list = []
    created_at: Any
    updated_at: Any


class LogframeResultCreateRequest(BaseModel):
    level: str = Field(min_length=2, max_length=32)
    statement: str = Field(min_length=2)
    code: Optional[str] = None
    assumptions: Optional[str] = None
    means_of_verification: Optional[str] = None
    parent_id: Optional[UUID] = None
    sort_order: int = 0


class LogframeResultResponse(ORMModel):
    id: UUID
    organization_id: UUID
    logframe_id: UUID
    parent_id: Optional[UUID] = None
    level: str
    code: Optional[str] = None
    statement: str
    assumptions: Optional[str] = None
    means_of_verification: Optional[str] = None
    sort_order: int
    created_at: Any
    updated_at: Any


class LogframeCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="draft", max_length=32)
    theory_of_change_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    results: Optional[list[LogframeResultCreateRequest]] = None


class LogframeUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    theory_of_change_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class LogframeResponse(ORMModel):
    id: UUID
    organization_id: UUID
    theory_of_change_id: Optional[UUID] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    name: str
    code: str
    description: Optional[str] = None
    status: str
    results: list[LogframeResultResponse] = []
    created_at: Any
    updated_at: Any


class IndicatorTargetCreateRequest(BaseModel):
    period_label: str = Field(min_length=1, max_length=128)
    target_value: float = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    status: str = Field(default="planned", max_length=32)


class IndicatorTargetResponse(ORMModel):
    id: UUID
    organization_id: UUID
    indicator_id: UUID
    period_label: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    target_value: Any
    notes: Optional[str] = None
    status: str
    created_at: Any
    updated_at: Any


class IndicatorCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    level: str = Field(default="outcome", max_length=32)
    measure_type: str = Field(default="quantitative", max_length=32)
    unit: Optional[str] = None
    direction: str = Field(default="increase", max_length=32)
    collection_method: Optional[str] = None
    frequency: Optional[str] = None
    baseline_value: Optional[float] = None
    baseline_date: Optional[date] = None
    status: str = Field(default="active", max_length=32)
    disaggregation: Optional[dict] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    logframe_result_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    targets: Optional[list[IndicatorTargetCreateRequest]] = None


class IndicatorUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    level: Optional[str] = Field(default=None, max_length=32)
    measure_type: Optional[str] = Field(default=None, max_length=32)
    unit: Optional[str] = None
    direction: Optional[str] = Field(default=None, max_length=32)
    collection_method: Optional[str] = None
    frequency: Optional[str] = None
    baseline_value: Optional[float] = None
    baseline_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=32)
    disaggregation: Optional[dict] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    logframe_result_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None


class IndicatorResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    logframe_result_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    name: str
    code: str
    description: Optional[str] = None
    level: str
    measure_type: str
    unit: Optional[str] = None
    direction: str
    collection_method: Optional[str] = None
    frequency: Optional[str] = None
    baseline_value: Optional[Any] = None
    baseline_date: Optional[date] = None
    status: str
    disaggregation: dict = {}
    targets: list[IndicatorTargetResponse] = []
    created_at: Any
    updated_at: Any


class MonitoringResultCreateRequest(BaseModel):
    indicator_id: UUID
    reporting_date: date
    actual_value: Optional[float] = None
    qualitative_value: Optional[str] = None
    status: str = Field(default="draft", max_length=32)
    target_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    data_source: Optional[str] = None
    location_label: Optional[str] = None
    notes: Optional[str] = None


class MonitoringResultUpdateRequest(BaseModel):
    reporting_date: Optional[date] = None
    actual_value: Optional[float] = None
    qualitative_value: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    target_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    data_source: Optional[str] = None
    location_label: Optional[str] = None
    notes: Optional[str] = None


class MonitoringResultResponse(ORMModel):
    id: UUID
    organization_id: UUID
    indicator_id: UUID
    target_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    reporting_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    actual_value: Optional[Any] = None
    qualitative_value: Optional[str] = None
    status: str
    data_source: Optional[str] = None
    location_label: Optional[str] = None
    notes: Optional[str] = None
    created_at: Any
    updated_at: Any


class EvaluationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    evaluation_type: str = Field(default="midline", max_length=32)
    status: str = Field(default="planned", max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evaluator_name: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    key_findings: Optional[str] = None
    recommendations: Optional[str] = None
    lessons_learned: Optional[str] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class EvaluationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    evaluation_type: Optional[str] = Field(default=None, max_length=32)
    status: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evaluator_name: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    key_findings: Optional[str] = None
    recommendations: Optional[str] = None
    lessons_learned: Optional[str] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class EvaluationResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    name: str
    code: str
    evaluation_type: str
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evaluator_name: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    key_findings: Optional[str] = None
    recommendations: Optional[str] = None
    lessons_learned: Optional[str] = None
    created_at: Any
    updated_at: Any


# -------- Phase 5: Communities / Households / Beneficiaries / Memberships --------


class CommunityCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    community_type: str = Field(default="village", max_length=64)
    status: str = Field(default="active", max_length=32)
    parent_id: Optional[UUID] = None
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    region: Optional[str] = None
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    population_estimate: Optional[int] = None
    notes: Optional[str] = None


class CommunityUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    community_type: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    parent_id: Optional[UUID] = None
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    region: Optional[str] = None
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    population_estimate: Optional[int] = None
    notes: Optional[str] = None


class CommunityResponse(ORMModel):
    id: UUID
    organization_id: UUID
    parent_id: Optional[UUID] = None
    name: str
    code: str
    community_type: str
    status: str
    country_code: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    latitude: Optional[Any] = None
    longitude: Optional[Any] = None
    population_estimate: Optional[int] = None
    notes: Optional[str] = None
    created_at: Any
    updated_at: Any


class HouseholdCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    status: str = Field(default="active", max_length=32)
    community_id: Optional[UUID] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    household_size: Optional[int] = None
    poverty_status: Optional[str] = None
    notes: Optional[str] = None


class HouseholdUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    community_id: Optional[UUID] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    household_size: Optional[int] = None
    poverty_status: Optional[str] = None
    notes: Optional[str] = None


class HouseholdResponse(ORMModel):
    id: UUID
    organization_id: UUID
    community_id: Optional[UUID] = None
    name: str
    code: str
    status: str
    address: Optional[str] = None
    latitude: Optional[Any] = None
    longitude: Optional[Any] = None
    household_size: Optional[int] = None
    poverty_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: Any
    updated_at: Any


class BeneficiaryMembershipCreateRequest(BaseModel):
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    membership_role: str = Field(default="participant", max_length=64)
    status: str = Field(default="enrolled", max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    exit_reason: Optional[str] = None
    notes: Optional[str] = None


class BeneficiaryMembershipUpdateRequest(BaseModel):
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    membership_role: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    exit_reason: Optional[str] = None
    notes: Optional[str] = None


class BeneficiaryMembershipResponse(ORMModel):
    id: UUID
    organization_id: UUID
    beneficiary_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    activity_id: Optional[UUID] = None
    membership_role: str
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    exit_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Any
    updated_at: Any


class BeneficiaryCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    middle_name: Optional[str] = Field(default=None, max_length=120)
    code: Optional[str] = Field(default=None, max_length=64)
    sex: Optional[str] = None
    date_of_birth: Optional[date] = None
    national_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: str = Field(default="active", max_length=32)
    registration_date: Optional[date] = None
    consent_data_use: bool = False
    consent_photo: bool = False
    is_household_head: bool = False
    vulnerability_tags: Optional[list] = None
    household_id: Optional[UUID] = None
    community_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    memberships: Optional[list[BeneficiaryMembershipCreateRequest]] = None


class BeneficiaryUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    middle_name: Optional[str] = Field(default=None, max_length=120)
    code: Optional[str] = Field(default=None, max_length=64)
    sex: Optional[str] = None
    date_of_birth: Optional[date] = None
    national_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[str] = Field(default=None, max_length=32)
    registration_date: Optional[date] = None
    consent_data_use: Optional[bool] = None
    consent_photo: Optional[bool] = None
    is_household_head: Optional[bool] = None
    vulnerability_tags: Optional[list] = None
    household_id: Optional[UUID] = None
    community_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


class BeneficiaryResponse(ORMModel):
    id: UUID
    organization_id: UUID
    household_id: Optional[UUID] = None
    community_id: Optional[UUID] = None
    code: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    sex: Optional[str] = None
    date_of_birth: Optional[date] = None
    national_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str
    registration_date: Optional[date] = None
    consent_data_use: bool
    consent_photo: bool
    is_household_head: bool
    vulnerability_tags: list = []
    latitude: Optional[Any] = None
    longitude: Optional[Any] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    memberships: list[BeneficiaryMembershipResponse] = []
    created_at: Any
    updated_at: Any


# -------- Phase 6: Reports / Dashboards / Maps / Evidence / Analytics --------


class ReportCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    report_type: str = Field(default="progress", max_length=64)
    status: str = Field(default="draft", max_length=32)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    sections: Optional[list] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    grant_id: Optional[UUID] = None


class ReportUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    report_type: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    sections: Optional[list] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    grant_id: Optional[UUID] = None


class ReportResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    grant_id: Optional[UUID] = None
    name: str
    code: str
    report_type: str
    status: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    sections: list = []
    created_at: Any
    updated_at: Any


class SavedDashboardCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="active", max_length=32)
    is_default: bool = False
    layout: Optional[dict] = None
    widgets: Optional[list] = None
    filters: Optional[dict] = None


class SavedDashboardUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    is_default: Optional[bool] = None
    layout: Optional[dict] = None
    widgets: Optional[list] = None
    filters: Optional[dict] = None


class SavedDashboardResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str] = None
    status: str
    is_default: bool
    layout: dict = {}
    widgets: list = []
    filters: dict = {}
    created_at: Any
    updated_at: Any


class MapFeatureCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    feature_type: str = Field(default="point", max_length=32)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geometry: Optional[dict] = None
    properties: Optional[dict] = None
    community_id: Optional[UUID] = None
    sort_order: int = 0


class MapFeatureResponse(ORMModel):
    id: UUID
    organization_id: UUID
    layer_id: UUID
    name: str
    feature_type: str
    latitude: Optional[Any] = None
    longitude: Optional[Any] = None
    geometry: Optional[dict] = None
    properties: dict = {}
    community_id: Optional[UUID] = None
    sort_order: int
    created_at: Any
    updated_at: Any


class MapLayerCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    layer_type: str = Field(default="sites", max_length=64)
    status: str = Field(default="active", max_length=32)
    description: Optional[str] = None
    style: Optional[dict] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    features: Optional[list[MapFeatureCreateRequest]] = None


class MapLayerUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    layer_type: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    description: Optional[str] = None
    style: Optional[dict] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class MapLayerResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    name: str
    code: str
    layer_type: str
    status: str
    description: Optional[str] = None
    style: dict = {}
    features: list[MapFeatureResponse] = []
    created_at: Any
    updated_at: Any


class EvidenceCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    evidence_type: str = Field(default="document", max_length=64)
    status: str = Field(default="draft", max_length=32)
    description: Optional[str] = None
    collected_on: Optional[date] = None
    source: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    tags: Optional[list] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    indicator_id: Optional[UUID] = None
    monitoring_result_id: Optional[UUID] = None
    evaluation_id: Optional[UUID] = None
    beneficiary_id: Optional[UUID] = None
    report_id: Optional[UUID] = None


class EvidenceUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    evidence_type: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    description: Optional[str] = None
    collected_on: Optional[date] = None
    source: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    tags: Optional[list] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    indicator_id: Optional[UUID] = None
    monitoring_result_id: Optional[UUID] = None
    evaluation_id: Optional[UUID] = None
    beneficiary_id: Optional[UUID] = None
    report_id: Optional[UUID] = None


class EvidenceResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    indicator_id: Optional[UUID] = None
    monitoring_result_id: Optional[UUID] = None
    evaluation_id: Optional[UUID] = None
    beneficiary_id: Optional[UUID] = None
    report_id: Optional[UUID] = None
    title: str
    code: str
    evidence_type: str
    status: str
    description: Optional[str] = None
    collected_on: Optional[date] = None
    source: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    tags: list = []
    created_at: Any
    updated_at: Any


class AnalyticsOverviewResponse(BaseModel):
    delivery: dict[str, Any] = {}
    finance: dict[str, Any] = {}
    meal: dict[str, Any] = {}
    field: dict[str, Any] = {}
    insights: dict[str, Any] = {}
    reports_by_status: dict[str, int] = {}
    evidence_by_type: dict[str, int] = {}


# -------- Phase 7: AI Copilot / Predictions / Narratives / Knowledge --------


class AiConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default="New conversation", max_length=255)
    context: dict[str, Any] = Field(default_factory=dict)


class AiConversationResponse(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    title: str
    status: str
    pinned: bool = False
    share_token: Optional[str] = None
    context: dict = {}
    metadata_: Optional[dict] = Field(default=None, serialization_alias="metadata")
    created_at: Any
    updated_at: Any


class AiMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    page_context: Optional[dict[str, Any]] = None


class AiMessageResponse(ORMModel):
    id: UUID
    organization_id: UUID
    conversation_id: UUID
    role: str
    content: str
    model: Optional[str] = None
    provider: str
    token_count: Optional[int] = None
    metadata_: Optional[dict] = Field(default=None, serialization_alias="metadata")
    created_at: Any
    updated_at: Any


class AiConversationDetailResponse(AiConversationResponse):
    messages: list[AiMessageResponse] = []


class AiConversationUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    pinned: Optional[bool] = None


class AiMessageFeedbackRequest(BaseModel):
    feedback: str = Field(pattern="^(up|down)$")


class AiInsightsScanRequest(BaseModel):
    persist: bool = False


class AiWorkflowDraftRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    page_context: Optional[dict[str, Any]] = None
    save: bool = False


class AiWorkflowDraftResponse(BaseModel):
    definition: dict[str, Any]
    explanation: str
    provider: str
    workflow_id: Optional[str] = None


class AiReportGenerateRequest(BaseModel):
    report_type: str = Field(default="monthly", max_length=64)
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    save_narrative: bool = False


class AiReportResponse(BaseModel):
    report_type: str
    title: str
    content: str
    provider: str
    model: Optional[str] = None
    generated_at: str
    narrative_id: Optional[str] = None


class AiPredictionGenerateRequest(BaseModel):
    prediction_type: str = Field(default="project_risk", max_length=64)
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class AiPredictionUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None, max_length=32)
    severity: Optional[str] = Field(default=None, max_length=32)
    title: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = None


class AiPredictionResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    prediction_type: str
    title: str
    summary: str
    severity: str
    score: Any
    status: str
    recommendations: list = []
    signals: dict = {}
    provider: str
    model: Optional[str] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class AiNarrativeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    narrative_type: str = Field(default="executive_summary", max_length=64)
    prompt: Optional[str] = None
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    report_id: Optional[UUID] = None


class AiNarrativeUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    content: Optional[str] = None
    narrative_type: Optional[str] = Field(default=None, max_length=64)


class AiNarrativeResponse(ORMModel):
    id: UUID
    organization_id: UUID
    program_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    report_id: Optional[UUID] = None
    name: str
    code: str
    narrative_type: str
    status: str
    prompt: Optional[str] = None
    content: str
    provider: str
    model: Optional[str] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class KnowledgeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    category: str = Field(default="guidance", max_length=64)
    status: str = Field(default="published", max_length=32)
    summary: Optional[str] = None
    content: str = Field(min_length=1)
    source: Optional[str] = Field(default=None, max_length=255)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    category: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    summary: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = Field(default=None, max_length=255)
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


class KnowledgeResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    category: str
    status: str
    summary: Optional[str] = None
    content: str
    source: Optional[str] = None
    tags: list = []
    embedding_ref: Optional[str] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


# -------- Phase 8: Marketplace / API keys / Integrations / White label --------


class MarketplaceAppResponse(ORMModel):
    id: UUID
    name: str
    code: str
    category: str
    summary: Optional[str] = None
    description: Optional[str] = None
    publisher: str
    pricing_tier: str
    status: str
    is_featured: bool
    icon_key: Optional[str] = None
    config_schema: dict = {}
    created_at: Any
    updated_at: Any


class MarketplaceInstallRequest(BaseModel):
    app_id: UUID
    config: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class MarketplaceInstallationUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None, max_length=32)
    config: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class MarketplaceInstallationResponse(ORMModel):
    id: UUID
    organization_id: UUID
    app_id: UUID
    status: str
    config: dict = {}
    notes: Optional[str] = None
    installed_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    expires_at: Optional[datetime] = None


class ApiKeyResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    key_prefix: str
    status: str
    scopes: list = []
    last_used_at: Optional[Any] = None
    expires_at: Optional[Any] = None
    created_by_id: Optional[UUID] = None
    revoked_at: Optional[Any] = None
    created_at: Any
    updated_at: Any


class ApiKeyCreatedResponse(ApiKeyResponse):
    secret: str


class IntegrationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(default="webhook", max_length=64)
    status: str = Field(default="active", max_length=32)
    direction: str = Field(default="outbound", max_length=32)
    endpoint_url: Optional[str] = Field(default=None, max_length=1024)
    secret: Optional[str] = Field(default=None, max_length=512)
    config: dict[str, Any] = Field(default_factory=dict)
    events: list[str] = Field(default_factory=list)


class IntegrationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    provider: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    direction: Optional[str] = Field(default=None, max_length=32)
    endpoint_url: Optional[str] = Field(default=None, max_length=1024)
    secret: Optional[str] = Field(default=None, max_length=512)
    config: Optional[dict[str, Any]] = None
    events: Optional[list[str]] = None


class IntegrationResponse(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    provider: str
    status: str
    direction: str
    endpoint_url: Optional[str] = None
    secret_hint: Optional[str] = None
    config: dict = {}
    events: list = []
    last_sync_at: Optional[Any] = None
    last_error: Optional[str] = None
    created_by_id: Optional[UUID] = None
    created_at: Any
    updated_at: Any


class BrandingUpdateRequest(BaseModel):
    product_name: Optional[str] = Field(default=None, max_length=255)
    tagline: Optional[str] = Field(default=None, max_length=255)
    primary_color: Optional[str] = Field(default=None, max_length=32)
    secondary_color: Optional[str] = Field(default=None, max_length=32)
    accent_color: Optional[str] = Field(default=None, max_length=32)
    logo_url: Optional[str] = Field(default=None, max_length=1024)
    favicon_url: Optional[str] = Field(default=None, max_length=1024)
    login_background_url: Optional[str] = Field(default=None, max_length=1024)
    custom_domain: Optional[str] = Field(default=None, max_length=255)
    support_email: Optional[str] = Field(default=None, max_length=255)
    support_url: Optional[str] = Field(default=None, max_length=512)
    hide_powered_by: Optional[bool] = None
    is_enabled: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class BrandingResponse(ORMModel):
    id: UUID
    organization_id: UUID
    product_name: Optional[str] = None
    tagline: Optional[str] = None
    primary_color: str
    secondary_color: str
    accent_color: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    login_background_url: Optional[str] = None
    custom_domain: Optional[str] = None
    support_email: Optional[str] = None
    support_url: Optional[str] = None
    hide_powered_by: bool
    is_enabled: bool
    metadata_: dict = Field(default_factory=dict, serialization_alias="metadata")
    created_at: Any
    updated_at: Any


class PublicBrandingResponse(BaseModel):
    organization_name: str
    organization_slug: str
    product_name: Optional[str] = None
    tagline: Optional[str] = None
    is_enabled: bool = False
    primary_color: str = "#0F766E"
    secondary_color: str = "#44403C"
    accent_color: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    login_background_url: Optional[str] = None
    support_email: Optional[str] = None
    support_url: Optional[str] = None
    hide_powered_by: bool = False
    custom_domain: Optional[str] = None
    metadata: dict = {}


class NotificationResponse(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    event_type: str
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    severity: str
    status: str
    read_at: Optional[Any] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    created_at: Any
    updated_at: Any


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class WebhookDeliveryResponse(ORMModel):
    id: UUID
    organization_id: UUID
    integration_id: UUID
    event_type: str
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: Optional[Any] = None
    delivered_at: Optional[Any] = None
    last_error: Optional[str] = None
    response_status: Optional[int] = None
    endpoint_url: Optional[str] = None
    created_at: Any
    updated_at: Any


TokenResponse.model_rebuild()
