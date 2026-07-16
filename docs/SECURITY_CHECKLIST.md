# ImpactFlow — Security checklist (Track C6)

Use before staging/pilot. Mark items as you verify.

## Secrets & config

- [ ] `APP_ENV=production` on staging/prod
- [ ] `JWT_SECRET_KEY` is ≥32 chars and not a placeholder
- [ ] `ENCRYPTION_KEY` is a valid Fernet key (not a placeholder)
- [ ] `.env` is never committed; deploy secrets via env/secret manager
- [ ] `BACKEND_CORS_ORIGINS` is an explicit allow-list (no `*`)

## Auth & tenancy

- [ ] Invite → force password change works
- [ ] Forgot/reset password works end-to-end
- [ ] Cross-org access denied (API tests green)
- [ ] API keys authenticate via `X-Api-Key` / `Bearer if_…` with scopes
- [ ] Rate limits active when Redis is available

## Surface area

- [ ] OpenAPI `/docs` and `/redoc` disabled in production
- [ ] `/health` for liveness; `/ready` for DB + Redis
- [ ] Audit logs written for invites, auth changes, and major mutations
- [ ] Temporary passwords / reset tokens never appear in logs or audit `changes`

## Ops

- [ ] HTTPS termination in front of API/web
- [ ] Database backups scheduled
- [ ] Demo seed not used with production credentials
