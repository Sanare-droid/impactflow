# Epic 6 — Integrations Hub, Open Platform & Developer Ecosystem

**API version:** 0.18.0 · **Migration:** `0017_phase17`

## Architecture (extends, does not rewrite)

| Layer | Approach |
|-------|----------|
| **Platform integrations** | Extended with encrypted credentials + connector enable |
| **Webhooks** | Enhanced with HMAC signing, inbound receiver, DLQ redrive |
| **API keys** | Existing auth reused; added rotate |
| **Event bus** | Standardized catalog; inbound webhooks emit events |
| **Marketplace** | Plugin manifests foundation for future installs |
| **Connectors** | Registry-based — new connectors plug in without core changes |

## Connector catalog

Production-ready definitions for: Microsoft 365, Google Workspace/Drive, OneDrive, Dropbox, Box, Kobo, ODK Central, SurveyCTO, ArcGIS, GeoJSON/Shapefile/QGIS export, Slack, Teams, Email, Twilio/WhatsApp (future-ready), QuickBooks, Xero (future-ready), CSV accounting, Power BI, Looker Studio, Tableau, CSV analytics, REST API, Webhook consumer/producer, OpenAPI.

## Key endpoints

| Area | Paths |
|------|-------|
| Catalog | `GET /connectors`, `POST /connectors/enable` |
| Lifecycle | `POST /integrations/{id}/health\|sync\|clone\|oauth/start` |
| Mapping | `GET/POST /field-mappings`, `POST .../preview` |
| Webhooks | `POST /webhooks/inbound/{token}`, `POST /webhooks/dead/redrive` |
| Monitoring | `GET /integrations/monitoring` |
| Developer | `GET /developer/portal\|events\|openapi` |
| Plugins | `GET /plugins` |
| API keys | `POST /api-keys/{id}/rotate` |

## Web

- `/app/integrations` — Gallery, Connections, API Keys, Webhooks, Monitoring, Mappings
- `/app/developer` — Developer Portal

## Security

- Credentials encrypted with existing Fernet `encrypt_secret`
- Secrets never returned in API responses
- Tenant-scoped queries; RBAC on all hub routes
- Outbound webhooks signed with `X-ImpactFlow-Signature`

## Delivered (Definition of Done)

- [x] Integrations Hub gallery + configure without custom code
- [x] Extensible connector framework/registry
- [x] OAuth start URLs + API key / bearer / webhook secret auth types
- [x] Sync jobs (pull/push, dry-run, incremental)
- [x] Field mapping profiles + preview
- [x] Webhook system enhanced (not replaced)
- [x] API key rotate + management UI
- [x] Developer Portal + OpenAPI download
- [x] Standardized event catalog
- [x] Marketplace/plugin foundation
- [x] Integration monitoring dashboard
- [x] Encrypted credentials
- [x] Tenant isolation + RBAC tests
- [x] API **0.18.0** · migration **0017**

## Deferred

- Full OAuth callback token exchange against live IdPs (authorize URL generation shipped)
- Live Kobo/ODK pull scheduling in worker (manual sync + health shipped)
- GraphQL connector
- Twilio/WhatsApp live send
