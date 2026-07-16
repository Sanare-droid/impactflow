# ImpactFlow — Deployment Plan

**Audience:** platform operators, DevOps, and technical leads  
**Current API:** 0.19.0 · **Stack:** FastAPI + Next.js + PostgreSQL/PostGIS + Redis  
**Related:** [DEPLOY.md](./DEPLOY.md) (quick commands) · [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) · [deploy/k8s](../deploy/k8s/README.md)

---

## 1. Purpose

This plan describes how to take ImpactFlow from a local development stack to a production-grade, multi-tenant deployment that supports:

- Horizontal API scaling
- Secure secrets and TLS
- Database migrations with low downtime
- White-label / custom domains
- Backups and disaster recovery
- Observability and health checks

Use [DEPLOY.md](./DEPLOY.md) for day-to-day commands. Use **this document** for phased rollout, ownership, and go-live gates.

---

## 2. Target architecture

```
                    ┌─────────────────┐
   Users / Orgs ───►│  CDN / Ingress  │── TLS termination
                    │  (custom domains)│
                    └────────┬────────┘
              ┌──────────────┴──────────────┐
              ▼                             ▼
     ┌────────────────┐           ┌─────────────────┐
     │  Web (Next.js) │           │  API (FastAPI)  │
     │  Vercel / k8s  │──────────►│  N replicas     │
     └────────────────┘           └────────┬────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
           ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
           │ Postgres+PostGIS│    │     Redis      │    │ Object storage │
           │  (managed)      │    │  (rate limit)  │    │ S3 / R2 / MinIO│
           └────────────────┘    └────────────────┘    └────────────────┘
```

| Component | Role | Scale notes |
|-----------|------|-------------|
| Web | UI, auth session client | Stateless; CDN-friendly |
| API | Business logic, RBAC, events | Scale replicas; workers ≥ 2 |
| Postgres + PostGIS | System of record | Managed; PITR backups |
| Redis | Rate limits / token helpers | Managed or Redis Cluster later |
| Object storage | Evidence, media, exports | S3-compatible |
| Optional OpenAI | AI Copilot | Key in secrets only |

---

## 3. Environments

| Environment | Purpose | Data | Secrets |
|-------------|---------|------|---------|
| **Local** | Developer machines | Disposable / seed | `.env` from `.env.example` |
| **Staging** | Pilot validation, UAT | Anonymized or demo | Secret manager; production-like |
| **Production** | Live organizations | Real tenant data | Secret manager only |

Rules:

1. Staging mirrors production topology (compose prod or k8s).
2. Never reuse production `JWT_SECRET_KEY` / `ENCRYPTION_KEY` in lower envs.
3. Demo seed (`seed_demo`) is for local/staging only — never with production credentials.

---

## 4. Phased rollout

### Phase A — Foundations (Week 0–1)

**Goal:** Secure staging online with HTTPS.

| Step | Owner | Done when |
|------|-------|-----------|
| Provision Postgres (PostGIS), Redis, object storage | Ops | Connection strings validated |
| Create staging secrets (JWT, Fernet, DB password) | Ops | [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) secrets section green |
| Deploy API via `docker-compose.prod.yml` or k8s | Ops | `/health` and `/ready` return ok |
| Deploy web with `NEXT_PUBLIC_API_URL` | Ops | Login page loads |
| Run `alembic upgrade head` | Ops | Schema at head (`0018_phase18`+) |
| Configure CORS + `FRONTEND_URL` | Ops | Browser login works |
| Enable TLS at load balancer / Vercel | Ops | No certificate warnings |

**Exit gate:** Staging URL works; cross-org isolation tests pass in CI.

### Phase B — Pilot readiness (Week 1–2)

**Goal:** One real organization can operate the product.

| Step | Owner | Done when |
|------|-------|-----------|
| Seed or create pilot org (no shared demo password) | Admin | Org admin can sign in |
| Complete onboarding wizard | Pilot admin | Theme + sector set |
| Invite 2–3 users with least-privilege roles | Pilot admin | MFA optional but recommended |
| Configure SMTP (or accept stub emails in staging) | Ops | Invite / reset emails arrive |
| Enable AI key if Copilot is in scope | Ops | `/app/copilot` responds |
| Configure 1 integration (e.g. Slack or CSV) | Pilot admin | Health check green |
| Schedule DB backups + restore drill | Ops | Restore tested once |
| Walk [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) | Security | Checklist signed off |

**Exit gate:** Pilot can create a program, enter monitoring data, and export a report.

### Phase C — Production cutover (Week 2–3)

**Goal:** Production go-live with rollback plan.

| Step | Owner | Done when |
|------|-------|-----------|
| Freeze schema changes (or plan maintenance window) | Tech lead | Change window agreed |
| Deploy production stack (compose prod or k8s) | Ops | Rolling deploy healthy |
| Point DNS for `app.` / `api.` | Ops | DNS + TLS verified |
| Create production org(s) or migrate staging data | Admin | Tenants isolated |
| Enable white-label / custom domains if needed | Admin | [WHITE_LABEL.md](./WHITE_LABEL.md) / [CUSTOM_DOMAIN.md](./CUSTOM_DOMAIN.md) |
| Set subscription plan for each org | Admin | Billing page shows plan |
| Turn on monitoring alerts (API 5xx, DB, Redis) | Ops | Alert fires on test |
| Document support contacts in branding metadata | Admin | Footer / support email set |

**Exit gate:** Production `/ready` green for 24h; first org completes a real workflow.

### Phase D — Hardening (ongoing)

- Horizontal Pod Autoscaler ([deploy/k8s/api-hpa.yaml](../deploy/k8s/api-hpa.yaml))
- Object storage for tenant backups / media
- Live Stripe provider (fields already on subscriptions)
- Production ACME automation for custom domains
- Full locale UI catalogs (packs already seeded)

---

## 5. Deployment options

### Option 1 — Production Docker Compose (smallest prod)

```bash
cp .env.example .env.prod
# Fill JWT_SECRET_KEY, ENCRYPTION_KEY, POSTGRES_PASSWORD,
# BACKEND_CORS_ORIGINS, FRONTEND_URL

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

- API runs `alembic upgrade head` then uvicorn with **2 workers**
- Postgres + Redis volumes persist on the host
- Web is **not** in prod compose — deploy separately (Vercel or static host)

### Option 2 — Split cloud (recommended for pilots)

| Piece | Host |
|-------|------|
| Web | Vercel — root `apps/web`, env `NEXT_PUBLIC_API_URL` |
| API | Railway / Fly — Docker from `apps/api` |
| DB / Redis | Managed providers with PostGIS |

### Option 3 — Kubernetes

1. Build/push `impactflow-api:<version>` image.
2. Apply ConfigMap + Secrets (never commit secrets).
3. Apply [api-deployment.yaml](../deploy/k8s/api-deployment.yaml) and [api-hpa.yaml](../deploy/k8s/api-hpa.yaml).
4. Run migrations as a Job **before** new pods take traffic.
5. Ingress: TLS, path `/` → web, `/api` or api host → API.
6. Probes: liveness `/health`, readiness `/ready`.

Rolling update policy in the stub uses `maxUnavailable: 0` for zero-downtime API deploys.

---

## 6. Configuration checklist

### Required (production)

| Variable | Notes |
|----------|--------|
| `APP_ENV=production` | Disables debug surfaces |
| `JWT_SECRET_KEY` | ≥32 chars, unique per env |
| `ENCRYPTION_KEY` | Fernet key (MFA, SSO secrets, connector secrets) |
| `DATABASE_URL` | `postgresql+asyncpg://…` |
| `REDIS_URL` | Required for rate limiting |
| `BACKEND_CORS_ORIGINS` | Exact JSON array of web origins — no `*` |
| `FRONTEND_URL` | Used in invite / password-reset links |
| `POSTGRES_PASSWORD` | Strong; not default |

### Strongly recommended

| Variable | Notes |
|----------|--------|
| `OPENAI_API_KEY` | AI Copilot |
| `S3_*` | Evidence / media |
| `SMTP_*` | Real invite and reset emails |
| `NEXT_PUBLIC_API_URL` | Web → API base URL |
| `NEXT_PUBLIC_APP_URL` | Canonical web URL |

Generate secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 7. Migration & release procedure

1. **CI green** on the release commit (ruff, pytest, web build).
2. **Backup** production database (snapshot or `pg_dump`).
3. **Announce** short maintenance if migration is long (Epic 7 `0018` is additive).
4. **Deploy API** with `alembic upgrade head` before or at container start.
5. **Deploy web** pointing at the new API version.
6. **Smoke test:**
   - `GET /health` → `version` matches release
   - `GET /ready` → database + redis true
   - Login → dashboard
   - Create/read one program (tenant check)
7. **Monitor** error rates for 30–60 minutes.

### Rollback

| Failure | Action |
|---------|--------|
| Bad web build | Redeploy previous web revision (Vercel instant) |
| API crash loop | Roll back image tag; keep DB if migration is forward-only additive |
| Bad migration | Restore DB from backup taken in step 2; redeploy previous API |

Prefer **additive** Alembic revisions (as Epics 1–7 have been). Avoid destructive downgrades in production.

---

## 8. Multi-tenant & white-label deploy notes

- Every organization is isolated by `organization_id`; never share DB users across “apps” as a substitute for tenancy.
- Custom domains: add DNS per [CUSTOM_DOMAIN.md](./CUSTOM_DOMAIN.md), verify in **Organization** admin, resolve branding with `GET /api/v1/public/branding-by-host`.
- CORS must include each white-label origin.
- Edge/CDN should forward `Host` correctly for branding-by-host.

---

## 9. Backups & disaster recovery

| Asset | RPO target (pilot) | Method |
|-------|--------------------|--------|
| Postgres | ≤ 24h (ideally ≤ 1h) | Managed automated backups + weekly restore drill |
| Redis | Best-effort | Ephemeral OK for rate limits |
| Object storage | ≤ 24h | Bucket versioning |
| Tenant logical export | On demand | Organization → **Export all data** / `GET /backups/export` |

After a regional incident:

1. Restore Postgres to last good snapshot.
2. Redeploy API/web to last known-good version.
3. Confirm `/ready`, then notify org admins.
4. Reconcile any in-flight sync jobs / workflow runs.

---

## 10. Observability

| Signal | Endpoint / UI |
|--------|----------------|
| Liveness | `GET /health` |
| Readiness | `GET /ready` |
| Platform snapshot | `/app/ops` · `GET /ops/observability` |
| Org adoption | `/app/customer-success` |
| Audit trail | `/app/audit` |
| Integration health | `/app/integrations` monitoring tab |

Alert on: `/ready` failures, elevated 5xx, DB connection errors, Redis down, disk on DB volume.

---

## 11. Go-live acceptance criteria

- [ ] Staging and production use separate secrets and databases  
- [ ] HTTPS everywhere; OpenAPI docs disabled or restricted in production  
- [ ] Migrations at head; CI green on the deployed commit  
- [ ] At least one org admin + one least-privilege user verified  
- [ ] Invite + password reset path tested with real SMTP (or documented stub limitation)  
- [ ] Cross-tenant isolation tests green  
- [ ] Database backup + one successful restore drill  
- [ ] Support email / status contact published to pilots  
- [ ] Rollback owner and procedure named  

---

## 12. Roles & RACI (suggested)

| Activity | Ops | Tech lead | Org admin | Security |
|----------|-----|-----------|-----------|----------|
| Infra & secrets | R | A | C | C |
| App release | C | R/A | I | C |
| Tenant setup / branding | I | C | R | I |
| Security sign-off | C | C | I | R/A |
| Backup drills | R | A | I | C |

R = Responsible, A = Accountable, C = Consulted, I = Informed

---

## 13. Document index

| Doc | Use when |
|-----|----------|
| [DEPLOY.md](./DEPLOY.md) | Quick start commands |
| [USER_MANUAL.md](./USER_MANUAL.md) | Teaching end users |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design |
| [EPIC7_ENTERPRISE.md](./EPIC7_ENTERPRISE.md) | SaaS / billing / domains |
| [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) | Pre-pilot security |
| [WHITE_LABEL.md](./WHITE_LABEL.md) | Branding packages |
| [CUSTOM_DOMAIN.md](./CUSTOM_DOMAIN.md) | DNS for portals |
| [PLUGIN_SDK.md](./PLUGIN_SDK.md) | Extension publishers |
