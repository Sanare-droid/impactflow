# ImpactFlow AI

Enterprise MEAL / project operating system for NGOs, donors, governments, and development partners.

## Phase 1 — Foundation (complete)

- Multi-tenant organizations
- Authentication (JWT access + rotating refresh tokens + MFA)
- User management & invitations
- RBAC (permission catalog + system roles)
- Audit logging
- Dashboard
- Next.js web app (auth, workspace shell, dark mode)

## Phase 3 — Grants & finance (complete)

- Donors
- Grants (linked to donors / programs / projects)
- Budgets + budget lines
- Finance transactions (income, expense, commitment, transfer)
- Permissions: `donors|budgets`:`read|manage` (+ existing grants/finance)
- UI: Donors, Grants, Budgets, Finance + funding snapshot on dashboard

## Stack

| Layer | Technology |
|-------|------------|
| Web | Next.js, TypeScript, Tailwind, TanStack Query |
| API | FastAPI, SQLAlchemy, Alembic |
| DB | PostgreSQL + PostGIS |
| Cache | Redis |
| Storage | MinIO (S3-compatible) |
| Infra | Docker Compose |

## Repository layout

```
apps/api     FastAPI backend
apps/web     Next.js frontend
apps/mobile  Expo field app
docker-compose.yml
```

## Quick start

> **Note:** API runtime is **Python 3.12** (Docker). Local Python 3.14 is not recommended.

### 1. Environment

```bash
cp .env.example .env
```

Generate secrets and put them in `.env`:

```bash
python -c "from cryptography.fernet import Fernet; import secrets; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode()); print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
```

### 2. Start backend (recommended)

```bash
docker compose up --build -d postgres redis minio api
```

### 3. Start web locally

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000 — create a workspace.

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

Optional: run web in Docker too (`docker compose --profile full up --build`). On Windows this is slower and more network-sensitive; local `npm run dev` is preferred.

## API surface (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create org + admin |
| POST | `/api/v1/auth/login` | Login (optional MFA) |
| POST | `/api/v1/auth/refresh` | Rotate refresh token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/auth/mfa/setup` | Begin TOTP setup |
| POST | `/api/v1/auth/mfa/enable` | Confirm MFA |
| GET | `/api/v1/organizations/current` | Tenant profile |
| GET | `/api/v1/users` | List members |
| POST | `/api/v1/users/invite` | Invite user |
| GET | `/api/v1/roles` | List roles |
| GET | `/api/v1/permissions` | Permission catalog |
| GET | `/api/v1/dashboard/stats` | Dashboard metrics |
| GET | `/api/v1/audit-logs` | Audit trail |

| GET/POST | `/api/v1/programs` | List / create programs |
| GET/PATCH/DELETE | `/api/v1/programs/{id}` | Program detail |
| GET/POST | `/api/v1/projects` | List / create projects |
| GET/PATCH/DELETE | `/api/v1/projects/{id}` | Project detail |
| GET/POST | `/api/v1/activities` | List / create activities |
| GET/POST | `/api/v1/work-plans` | List / create work plans |
| GET/POST | `/api/v1/tasks` | List / create tasks |
| PATCH/DELETE | `/api/v1/tasks/{id}` | Update / delete tasks |

Send `Authorization: Bearer <access_token>` and `X-Organization-Id: <uuid>` on tenant routes.

## Default roles

- `org_admin` — full tenant access  
- `manager` — programs / projects / reporting  
- `meal_officer` — indicators, surveys, reports  
- `field_officer` — beneficiaries & surveys  
- `viewer` — read-only  

## Security model

- Passwords hashed with bcrypt  
- Short-lived JWT access tokens  
- Refresh tokens stored hashed, rotated, revocable  
- MFA secrets encrypted at rest (Fernet)  
- Permission checks on every protected route  
- Audit log on auth and admin mutations  
- Tenant isolation via `organization_id` + membership  

## Tests

```bash
cd apps/api
pytest
```

## Definition of done — Phase 1

- [x] Database schema + Alembic migration  
- [x] Auth / org / users / RBAC / audit APIs  
- [x] Web UI (landing, auth, dashboard, users, roles, audit, settings/MFA)  
- [x] Permissions enforced  
- [x] Audit logging  
- [x] Docker Compose  
- [x] Documentation  

## Next: Phase 7

AI Copilot → Predictions → Narratives → Knowledge Base

## Definition of done — Phase 2

- [x] Database schema + Alembic `0002_phase2`
- [x] Program / project / activity / work plan / task APIs
- [x] Permissions + audit on mutations
- [x] Web UI (programs, projects, tasks, dashboard metrics)
- [x] System role permission sync on API startup

## Definition of done — Phase 3

- [x] Database schema + Alembic `0003_phase3`
- [x] Donor / grant / budget / finance transaction APIs
- [x] Permissions + audit on mutations
- [x] Web UI (donors, grants, budgets, finance, funding snapshot)

## Definition of done — Phase 4

- [x] Database schema + Alembic `0004_phase4`
- [x] Theory of Change / Logframe / Indicator / Target / Monitoring / Evaluation APIs
- [x] Permissions + audit on mutations
- [x] Web UI (MEAL pages + dashboard MEAL snapshot)

## Definition of done — Phase 5

- [x] Database schema + Alembic `0005_phase5`
- [x] Community / Household / Beneficiary / Membership APIs
- [x] Permissions + audit on mutations
- [x] Web UI (communities, households, beneficiaries + field caseload snapshot)
- [x] Expo field app scaffold (`apps/mobile`) for login + beneficiary registration

## Definition of done — Phase 6

- [x] Database schema + Alembic `0006_phase6`
- [x] Report / Saved Dashboard / Map Layer+Feature / Evidence APIs
- [x] Analytics overview endpoint aggregating Phases 2–6
- [x] Permissions + audit on mutations
- [x] Web UI (reports, dashboards, analytics, maps, evidence)

## Definition of done — Phase 7

- [x] Database schema + Alembic `0007_phase7`
- [x] AI Copilot / Predictions / Narratives / Knowledge Base APIs
- [x] OpenAI provider with deterministic fallback when no API key
- [x] Permissions + audit on mutations
- [x] Web UI (copilot, predictions, narratives, knowledge + dashboard AI snapshot)

## Definition of done — Phase 8

- [x] Database schema + Alembic `0008_phase8`
- [x] Marketplace catalog + installs, API keys, integrations, white-label branding
- [x] Public branding endpoint by org slug
- [x] Permissions + audit on mutations
- [x] Web UI (marketplace, integrations/API keys, branding + dashboard platform snapshot)
