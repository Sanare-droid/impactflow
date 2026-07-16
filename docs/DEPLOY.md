# Deploying ImpactFlow AI

> **Full rollout plan:** [DEPLOYMENT_PLAN.md](./DEPLOYMENT_PLAN.md) (phases, RACI, go-live gates)  
> **End-user guide:** [USER_MANUAL.md](./USER_MANUAL.md)

## Local development (default)

```bash
cp .env.example .env
# set JWT_SECRET_KEY + ENCRYPTION_KEY
docker compose up -d postgres redis minio api
cd apps/web && npm install && npm run dev
```

- API: http://localhost:8000/docs  
- Web: http://localhost:3000  

## Production Compose

Use `docker-compose.prod.yml` (no source bind mounts, no `--reload`, workers enabled).

```bash
cp .env.example .env.prod
# Set strong secrets — production refuses placeholder JWT/ENCRYPTION keys
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Required production env:

| Variable | Notes |
|----------|--------|
| `JWT_SECRET_KEY` | ≥32 chars, not a placeholder |
| `ENCRYPTION_KEY` | Valid Fernet key |
| `POSTGRES_PASSWORD` | Strong DB password |
| `BACKEND_CORS_ORIGINS` | Exact web origins JSON array |
| `FRONTEND_URL` | Used in invite/reset emails |

## Demo seed

```bash
docker compose exec api python -m app.scripts.seed_demo
```

Defaults: org slug `demo`, email `demo@impactflow.local`, password `DemoPass12345!`.

Override with `DEMO_ORG_SLUG`, `DEMO_ADMIN_EMAIL`, `DEMO_ADMIN_PASSWORD`.

## Suggested cloud layout

| Component | Suggested host |
|-----------|----------------|
| Web (Next.js) | [Vercel](https://vercel.com) — root `apps/web`, env `NEXT_PUBLIC_API_URL` |
| API (FastAPI) | [Railway](https://railway.app) / Fly.io — Docker from `apps/api` |
| Postgres + PostGIS | Managed Postgres with PostGIS extension |
| Redis | Managed Redis (rate limiting) |
| Object storage | S3 / R2 / MinIO |

### Web on Vercel

1. Import the GitHub repo  
2. Root directory: `apps/web`  
3. Env: `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`  
4. Build: `npm run build`

### API on Railway / Fly

1. Deploy from `apps/api` Dockerfile  
2. Attach Postgres + Redis  
3. Set secrets from the table above  
4. Run migrations via start command (`alembic upgrade head` already in Compose prod)

## API key authentication

Organization API keys (Integrations page) authenticate as:

```http
X-Api-Key: if_...
X-Organization-Id: <uuid>   # optional; key is already org-scoped
```

Or:

```http
Authorization: Bearer if_...
```

Scopes:

- `read` — all `*:read` / `ai:use` / `*:export` permissions  
- `write` / `manage` — manage + read  
- exact codes (e.g. `programs:read`)  

## Health

`GET /health` → `{ "status": "ok", "version": "0.19.0", ... }` (liveness)

`GET /ready` → `{ "status": "ready", "checks": { "database": true, "redis": true } }` (readiness; 503 if either dependency is down)

## Related

- [Deployment plan](./DEPLOYMENT_PLAN.md)  
- [User manual](./USER_MANUAL.md)  
- [Architecture](./ARCHITECTURE.md)  
- [Epic 7 Enterprise SaaS](./EPIC7_ENTERPRISE.md)  
- [Kubernetes stubs](../deploy/k8s/README.md)  
- [Gaps & polish plan](./GAPS_AND_POLISH_PLAN.md)
