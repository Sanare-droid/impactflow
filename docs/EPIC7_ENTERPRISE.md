# Epic 7 — Enterprise SaaS, White Label, Marketplace & Global Readiness

**API version:** 0.19.0 · **Migration:** `0018_phase18`

## Architecture (extends, does not rewrite)

| Layer | Approach |
|-------|----------|
| **Branding** | Extended Phase 8 `OrgBranding` + metadata packages (terms, CSS tokens, footer) |
| **Domains** | New `organization_domains` with DNS verify + SSL status; public resolve by host |
| **Billing** | Provider-agnostic plans/subscriptions (`internal` \| `stripe` \| `manual`) |
| **Feature flags** | Plan + org + role + region + environment resolution |
| **Marketplace** | Install now wires matching Integrations Hub connectors via `marketplace_code` |
| **Plugin SDK** | `app/plugins/sdk.py` — register routes/panels/actions without core patches |
| **Onboarding** | Wizard state + theme presets applied to branding |
| **SSO** | Encrypted OIDC/SAML config foundation (Azure AD / Google ready) |
| **Backups** | Tenant restore points + JSON export |
| **i18n** | Installable localization packs (en, fr, es, ar, pt, sw) |
| **Ops / CS** | Observability snapshot + customer success health score |

## Key endpoints

| Area | Paths |
|------|-------|
| Billing | `GET /billing/plans`, `GET /billing/subscription`, `POST /billing/subscription/change` |
| Flags | `GET /features`, `GET /feature-flags` |
| Domains | `GET/POST /domains`, `POST /domains/{id}/verify`, `GET /public/branding-by-host` |
| Onboarding | `GET/PATCH /onboarding`, `GET /onboarding/theme-presets` |
| Admin | `PATCH /admin/settings` |
| Backups | `GET/POST /backups`, `GET /backups/export` |
| SSO | `GET/PUT /sso` |
| Locales | `GET /locales` |
| Success / Ops | `GET /customer-success`, `GET /ops/observability` |
| SDK | `GET /plugin-sdk/manifest` |

## Web

- `/app/organization` — Admin console (settings, domains, SSO, backups, locales)
- `/app/billing` — Plans, subscription, feature flags
- `/app/branding` — White-label + live preview + legal/footer metadata
- `/app/onboarding` — Guided setup wizard
- `/app/customer-success` — Health / adoption
- `/app/ops` — Platform observability
- `/app/marketplace` — Templates & connectors (install → hub wiring)

## Security

- Tenant isolation on all org-scoped queries
- SSO secrets via existing Fernet `encrypt_secret`
- New RBAC: `billing:*`, `security:manage`, `backups:manage`
- Custom domains unique globally; cross-org verify → 404

## Delivered (Definition of Done)

- [x] White-label workspace (colors, logo, domain, metadata packages)
- [x] Custom domains + verification + host branding resolve
- [x] Subscription management (Free → Government, trials, coupons)
- [x] Feature flags by plan / org / role / region / env
- [x] Marketplace install → connector enable
- [x] Plugin SDK contract + builder
- [x] Enterprise onboarding wizard
- [x] Customer success dashboard
- [x] Localization architecture + 6 language packs
- [x] SSO / SCIM-ready foundations
- [x] Tenant backups + export
- [x] Ops observability
- [x] Docs (this file + Plugin SDK + deploy k8s stub)
- [x] API **0.19.0** · migration **0018**
- [x] Tenant isolation tests

## Deferred (future hardening)

- Live Stripe payment capture (provider fields ready)
- Production DNS/ACME certificate automation
- Full SAML assertion exchange + SCIM provisioning runtime
- Complete WCAG audit suite + a11y CI gate
- Full UI string catalogs per locale (architecture shipped)
- Multi-region active-active DR

## Related guides

- [Plugin SDK](PLUGIN_SDK.md)
- [White Label](WHITE_LABEL.md)
- [Deploy](DEPLOY.md)
- [Custom Domain](CUSTOM_DOMAIN.md)
- [Kubernetes](../deploy/k8s/README.md)
