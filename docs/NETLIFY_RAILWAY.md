# Deploy ImpactFlow: Netlify (web) + Railway (API)

This guide fixes the common monorepo mistakes:

- **Railway Railpack error** — builder scanned the **repo root** (compose + `apps/`) and found no Python/Node app.
- **Netlify 404** — site must use the **Next.js plugin** with base `apps/web`, not a static publish of the repo root.

---

## Architecture

| Service | Host | Path in repo |
|---------|------|----------------|
| Web (Next.js) | Netlify | `apps/web` |
| API (FastAPI) | Railway | `apps/api` (Docker via root `Dockerfile`) |
| Postgres (+ PostGIS) | Railway plugin | — |
| Redis | Railway plugin | — |

Repo helpers:

- `railway.toml` + root `Dockerfile` → API image from monorepo root  
- `netlify.toml` → Next build in `apps/web` + `@netlify/plugin-nextjs`

---

## Part A — Railway (API)

### 1. Create project & add data stores

1. New Railway project.
2. Add **PostgreSQL**. After it is up, open Query / connect and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
   ImpactFlow’s first migration requires PostGIS.
3. Add **Redis**.

### 2. Deploy the API service

1. **New service** → **GitHub** → `Sanare-droid/impactflow`.
2. **Do not** leave Railpack guessing at the root without config.
   - Preferred: keep **Root Directory empty** so root `railway.toml` applies (`builder = DOCKERFILE`, `Dockerfile`).
   - Alternative: set **Root Directory** = `apps/api` and use that folder’s Dockerfile.
3. Redeploy / trigger a new build. You should see a **Docker** build of the API, not Railpack scanning `.github/` and `docs/`.

### 3. Variables (API service)

**Critical — database must not be localhost.** Your crash
`Connect call failed ('127.0.0.1', 5432)` means `DATABASE_URL` was missing
or still the local default.

1. Open the **API** service → **Variables**.
2. **Add variable** → **Add a reference** (or Shared Variables):
   - From the Postgres service, reference `DATABASE_URL`
     (Railway UI often shows `${{Postgres.DATABASE_URL}}`).
3. Do the same for Redis: reference `REDIS_URL` / `REDIS_PRIVATE_URL`
   as `REDIS_URL`.
4. Or paste the Postgres URL manually and ensure the host is the **Railway
   internal hostname** (e.g. `postgres.railway.internal` or the public proxy host),
   **not** `localhost` / `127.0.0.1`.

ImpactFlow accepts `postgres://…` and `postgresql://…` and rewrites them to
`postgresql+asyncpg://…` automatically.

Generate secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

| Variable | Example / notes |
|----------|------------------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `JWT_SECRET_KEY` | long random string |
| `ENCRYPTION_KEY` | Fernet key |
| `DATABASE_URL` | **Reference from Postgres plugin** (required) |
| `REDIS_URL` | **Reference from Redis plugin** (required) |
| `FRONTEND_URL` | `https://YOUR-SITE.netlify.app` (update after Netlify deploy) |
| `BACKEND_CORS_ORIGINS` | `["https://YOUR-SITE.netlify.app"]` exact JSON array |
| `SUPERADMIN_EMAIL` | optional — platform superadmin email (created on boot) |
| `SUPERADMIN_PASSWORD` | optional — 12+ chars; pairs with SUPERADMIN_EMAIL |
| `OPENAI_API_KEY` | optional |

Netlify deploy URLs (`*.netlify.app`) are also allowed via `BACKEND_CORS_ORIGIN_REGEX` by default.

Also run once against the DB (Query tab or `psql`):

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Start command is already in the root `Dockerfile`:

`alembic upgrade head && uvicorn … --port $PORT`

### 4. Public URL & smoke test

1. Railway → API service → **Settings** → **Networking** → generate domain.
2. Open:
   - `https://YOUR-API.up.railway.app/health`
   - `https://YOUR-API.up.railway.app/ready`  
   Expect `database: true`, `redis: true`.

If `/ready` fails, fix `DATABASE_URL` / `REDIS_URL` / PostGIS before wiring Netlify.

---

## Part B — Netlify (web)

### 1. New site from Git

1. Netlify → **Add new site** → import `Sanare-droid/impactflow`.
2. Config is in root `netlify.toml` (`base = apps/web`, Next plugin). You usually **do not** need to override base/publish in the UI.
3. **Environment variables** (Site settings → Environment):

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-API.up.railway.app` (no trailing slash) |
| `NEXT_PUBLIC_APP_URL` | `https://YOUR-SITE.netlify.app` |
| `NEXT_PUBLIC_APP_NAME` | `ImpactFlow` (optional) |

4. Deploy. Build log should mention **@netlify/plugin-nextjs** and compile `apps/web`.

### 2. If you still see 404 on `/`

Checklist:

1. Build used `apps/web`, not the monorepo root as a static site.
2. Plugin `@netlify/plugin-nextjs` is installed (declared in `netlify.toml`).
3. `NEXT_PUBLIC_API_URL` is set **before** build (it is inlined at build time).
4. Clear cache and redeploy after changing env vars.
5. Open the deploy URL from the successful deploy (not an old failed one).

Browser **Network** tab: if `/` is 404 from Netlify CDN, the Next runtime is wrong. If `/` loads but `localhost:8000` or wrong host is called, fix `NEXT_PUBLIC_API_URL` and redeploy.

---

## Part C — Connect both

1. Set Railway `FRONTEND_URL` + `BACKEND_CORS_ORIGINS` to the **live** Netlify URL.
2. Redeploy **API** (CORS is read at runtime).
3. Confirm Netlify `NEXT_PUBLIC_API_URL` matches Railway API; redeploy **web** if you changed it.
4. Test: open Netlify site → Register / Sign in → Dashboard.

CORS must match exactly (scheme + host, no path). Example:

```json
["https://impactflow.netlify.app"]
```

If you add a custom domain later, add that origin too.

---

## Troubleshooting (matches recent errors)

| Symptom | Cause | Fix |
|---------|--------|-----|
| Railpack: “could not determine how to build” listing `./apps`, `docs` | Builder at **repo root** without Docker config | Use committed `railway.toml` + root `Dockerfile`, or set root dir `apps/api` |
| Railpack: “Script start.sh not found” | Same — wrong builder | Switch to Dockerfile builder |
| Alembic / API: `127.0.0.1:5432` connection refused | `DATABASE_URL` not set or still localhost | Link Postgres → API via variable reference; redeploy |
| Alembic: `No module named 'psycopg2'` | Railway `postgresql://` URL used as sync driver | App normalizes to `postgresql+asyncpg://` — redeploy latest `main` |
| Netlify: `(index):1 404` | Static deploy / wrong base / no Next plugin | Use `netlify.toml`; redeploy |
| API CORS errors in browser | `BACKEND_CORS_ORIGINS` missing Netlify origin | Update + restart API (or rely on `*.netlify.app` regex) |
| `Failed to fetch` / cannot reach API | Web still on localhost API or wrong URL | Set `NEXT_PUBLIC_API_URL` to Railway HTTPS URL and **redeploy Netlify** |
| `/ready` database false | Bad `DATABASE_URL` or no PostGIS | Fix URL scheme + `CREATE EXTENSION postgis` |
| Login works locally only | Web still pointing at localhost API | Rebuild Netlify with correct `NEXT_PUBLIC_API_URL` |

---

## Related

- [DEPLOY.md](./DEPLOY.md) — quick commands  
- [DEPLOYMENT_PLAN.md](./DEPLOYMENT_PLAN.md) — phased go-live  
- [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md)
