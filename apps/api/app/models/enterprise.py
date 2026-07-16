"""Epic 7 — enterprise SaaS: billing, flags, domains, SSO, backups, onboarding."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONType


class SubscriptionPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Catalog of SaaS plans — provider-agnostic (Stripe-ready, not coupled)."""

    __tablename__ = "subscription_plans"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(
        String(32), nullable=False, default="starter", index=True
    )  # free | starter | professional | enterprise | government | custom
    billing_period: Mapped[str] = mapped_column(
        String(16), nullable=False, default="monthly"
    )  # monthly | annual | custom
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    price_annual: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    seat_limit: Mapped[Optional[int]] = mapped_column(Integer)  # null = unlimited
    storage_gb: Mapped[Optional[int]] = mapped_column(Integer)
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    features: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class OrganizationSubscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-tenant subscription state — billing provider adapters plug in later."""

    __tablename__ = "organization_subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_org_subscriptions_org"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="trialing", index=True
    )  # trialing | active | past_due | suspended | cancelled | grace
    billing_period: Mapped[str] = mapped_column(String(16), nullable=False, default="monthly")
    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, default="internal"
    )  # internal | stripe | manual
    provider_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(String(255))
    coupon_code: Mapped[Optional[str]] = mapped_column(String(64))
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class FeatureFlag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Feature flags scoped by plan, org, role, region, or environment."""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("code", name="uq_feature_flags_code"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    default_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Targeting rules: plans[], organizations[], roles[], regions[], environments[], beta_groups[]
    rules: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class OrganizationDomain(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Custom domain / subdomain for white-label portals."""

    __tablename__ = "organization_domains"
    __table_args__ = (
        UniqueConstraint("hostname", name="uq_organization_domains_hostname"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )  # pending | verifying | active | failed | disabled
    verification_token: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ssl_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | active | expiring | failed
    dns_records: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    redirect_to_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class SsoConfiguration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Enterprise SSO foundation — SAML / OIDC / Azure AD / Google ready."""

    __tablename__ = "sso_configurations"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_sso_org_provider"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(64), nullable=False, default="oidc"
    )  # oidc | saml | azure_ad | google | okta
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    # Non-secret config (endpoints, entity ids); secrets go encrypted in secrets_
    config: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    secrets_: Mapped[dict] = mapped_column("secrets", JSONType, default=dict, nullable=False)
    enforce_sso: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scim_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowed_domains: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class TenantBackup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tenant backup / restore point metadata."""

    __tablename__ = "tenant_backups"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )  # pending | completed | failed | restoring
    backup_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="full"
    )  # full | incremental | export
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[Optional[str]] = mapped_column(String(128))
    storage_uri: Mapped[Optional[str]] = mapped_column(String(1024))
    include: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    manifest: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class OnboardingState(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Organization onboarding wizard progress."""

    __tablename__ = "onboarding_states"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_onboarding_states_org"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="in_progress", index=True
    )  # in_progress | completed | skipped
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="welcome")
    checklist: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(128))
    country_code: Mapped[Optional[str]] = mapped_column(String(2))
    theme_preset: Mapped[Optional[str]] = mapped_column(String(64))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)


class LocalizationPack(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Installable language packs — architecture for unlimited languages."""

    __tablename__ = "localization_packs"
    __table_args__ = (
        UniqueConstraint("locale", "version", name="uq_localization_packs_locale_version"),
    )

    locale: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    native_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    direction: Mapped[str] = mapped_column(String(8), nullable=False, default="ltr")  # ltr | rtl
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    coverage_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    strings: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)
