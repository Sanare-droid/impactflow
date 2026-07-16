# Custom domain checklist (white-label)

Use this when an organization enables branding with a `custom_domain`.

## DNS

1. Ask the org for their preferred hostname (e.g. `meal.example.org`).
2. Create a **CNAME** (or ALIAS/ANAME at apex) pointing to your ImpactFlow web host.
3. Wait for DNS propagation; verify with `dig meal.example.org`.
4. Issue TLS certificate (Let’s Encrypt / cloud LB managed cert).

## App configuration

1. In **White label**, set `custom_domain` and enable branding.
2. Set `FRONTEND_URL` / `NEXT_PUBLIC_APP_URL` for the tenant hostname when terminating TLS.
3. Ensure `BACKEND_CORS_ORIGINS` includes `https://meal.example.org`.
4. Login should load branding via `GET /api/v1/public/branding/{slug}` (org slug still required for multi-tenant login unless you map domain → slug at the edge).

## Optional edge mapping

At the reverse proxy / CDN, map `Host: meal.example.org` → org slug cookie or rewrite so the login page can skip the slug field.

## Verification

- [ ] HTTPS loads without certificate warnings
- [ ] Login shows org product name / colors / logo
- [ ] API CORS allows the custom origin
- [ ] Password reset emails use the correct `FRONTEND_URL`
