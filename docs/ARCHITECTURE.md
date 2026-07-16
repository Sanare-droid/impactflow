# ImpactFlow AI — Architecture (Phase 1)

## Principles

- API-first, multi-tenant, permissioned, audited
- Business logic in services; routes are thin
- Configuration via environment only
- No hardcoded tenant or role assumptions in UI

## Tenant model

```
Organization (tenant)
  └── Roles (+ RolePermissions → Permissions)
  └── Memberships (User ↔ Org ↔ Role)
  └── Domain data (Phase 2+) always carries organization_id
```

Request context resolves:

1. JWT access token (`sub`, optional `org_id`)
2. Optional `X-Organization-Id` header (overrides token org)
3. Live membership + permission set from DB

## Auth flow

1. Register org → seed permission catalog + system roles → create admin membership → issue tokens
2. Login → lockout check → password verify → optional MFA → issue tokens
3. Refresh → revoke old hash → rotate new hash
4. Logout → revoke refresh hash

## Permission codes

Format: `<module>:<action>` (see `app/core/permissions.py`).

Org admins receive the full catalog. Least-privilege roles are `manager`, `meal_officer`, `field_officer`, `viewer`.

## Audit

`audit_logs` stores actor, action, resource, org, IP, user agent, changes JSON. Written from auth and admin mutation paths.

## Frontend

- TanStack Query for server state
- Auth session in `localStorage` (`if_access_token`, `if_refresh_token`, `if_organization_id`)
- App shell routes under `/app/*`
- Theme via `next-themes` (system / light / dark)

## Phase 2 domain hierarchy

```
Organization
  └── Program
        └── Project
              ├── Activity
              ├── WorkPlan
              └── Task (optional activity_id / work_plan_id)
```

All entities carry `organization_id` and are resolved only within `RequestContext.organization`.

## Phase 3 finance hierarchy

```
Organization
  └── Donor
        └── Grant (optional program_id / project_id)
              ├── Budget
              │     └── BudgetLine
              └── FinanceTransaction
```

## Phase 4 MEAL hierarchy

```
Organization
  └── TheoryOfChange (optional program_id / project_id)
        └── Logframe
              └── LogframeResult (impact | outcome | output | activity)
                    └── Indicator
                          ├── IndicatorTarget
                          └── MonitoringResult
  └── Evaluation (optional program_id / project_id)
```

## Phase 5 field / beneficiary hierarchy

```
Organization
  └── Community
        └── Household
              └── Beneficiary
                    └── BeneficiaryMembership (program / project / activity)
```

## Phase 6 insights hierarchy

```
Organization
  ├── Report (optional program / project / grant)
  ├── SavedDashboard (widgets + layout JSON)
  ├── MapLayer
  │     └── MapFeature (point / polygon GeoJSON)
  └── EvidenceItem (links to program / indicator / evaluation / beneficiary / report)
```

Analytics overview aggregates counts across delivery, finance, MEAL, field, and insights.

## Phase 7 AI hierarchy

```
Organization
  ├── AiConversation
  │     └── AiMessage (user | assistant)
  ├── AiPrediction (risk / delivery signals)
  ├── AiNarrative (donor / executive drafts)
  └── KnowledgeDocument (SOP / guidance for grounded answers)
```

Provider: OpenAI Chat Completions when `OPENAI_API_KEY` is set; otherwise deterministic heuristic fallback. Copilot retrieves matching published knowledge docs via text search.

## Phase 8 platform hierarchy

```
Organization
  ├── MarketplaceInstallation → MarketplaceApp (catalog)
  ├── OrgApiKey (hashed secret, shown once)
  ├── IntegrationConnection (webhook / kobo / slack / …)
  └── OrgBranding (white-label colors, logo, domain)

Public
  └── GET /api/v1/public/branding/{slug}
```

## Future modules

All new modules must:

1. Add `organization_id` FK / index
2. Register permissions in catalog
3. Enforce `require_permissions(...)`
4. Write audit events for mutations
5. Keep API schemas separate from ORM models
