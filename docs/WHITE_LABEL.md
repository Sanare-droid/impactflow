# White Label Guide

ImpactFlow workspaces can operate entirely under an organization identity.

## Brand surfaces

| Surface | Where |
|---------|--------|
| Logo, favicon, colors, tagline | `OrgBranding` + `/app/branding` |
| Login / splash / CSS tokens | `metadata.css_tokens`, `login_background_url` |
| Terms, privacy, footer, email | `metadata.terms_url`, `privacy_url`, `footer` |
| Custom domain | `organization_domains` + `custom_domain` |
| Theme presets | Onboarding theme presets |

## Public resolve

- By slug: `GET /api/v1/public/branding/{slug}`
- By host: `GET /api/v1/public/branding-by-host?host=portal.example.org`

## Domains

1. Add hostname in Organization admin (`POST /domains`).
2. Publish TXT + CNAME records from the response.
3. Call verify (simulation in v0.19; production hooks ACME/DNS later).
4. Primary domain mirrors onto branding for login URLs.

## Brand packages

Reuse via branding `metadata` (theme preset code, CSS tokens, legal links). Apply presets from onboarding or branding UI.
