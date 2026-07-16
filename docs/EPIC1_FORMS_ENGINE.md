# ImpactFlow V1.1 — Epic 1: Dynamic Forms Engine

## Codebase analysis (pre-implementation)

### Architecture preserved
- FastAPI thin routers → services → SQLAlchemy; org-scoped queries; `write_audit_log`
- JWT + `X-Organization-Id` / API keys; permissions `<module>:<action>`
- Web: Next.js, teal/stone + Manrope/Source Serif
- Mobile: Expo + SQLite mutation queue; server-wins conflicts

### Foundation extended (Track E surveys — **not rebuilt**)
Survey **is** the form engine. No parallel Form product.

| Epic entity | ImpactFlow mapping |
|-------------|-------------------|
| Form | `Survey` (+ category, schedule, anonymity, limits, activity) |
| FormVersion | `SurveyVersion` (rich JSON schema v2) |
| Section / Field / Option / Validation | Inside versioned JSON + `form_schema` registry |
| FormAssignment | `survey_assignments` |
| SurveyResponse / SurveyAnswer / Attachment | Extended response + normalized answers + attachments |

---

## Delivered (API 0.13.0 · migration `0012_phase12`)

### Field types (registry in `app/services/form_schema.py`)
text, long_text, rich_text, number, decimal, currency, date, time, datetime, email, phone, url, boolean, checkbox, radio, dropdown, multi_select, gps, image, video, audio, file, signature, qr_code, barcode, matrix, rating, slider, repeat_group, section_header — extensible without migrations.

### Form features
Required, conditional `show_if`, calculated (`sum`), hidden, defaults, validation (min/max/regex), read-only, pages/sections, progress bar settings, draft save, autosave-ready PATCH, offline sync via `client_mutation_id`.

### Survey features
Builder, versioning, publish, archive, clone, schedule (`starts_at`/`ends_at`), assignments, expiry window, anonymous flag, response limits, skip/branch logic, question groups (sections), JSON import/export.

### API
CRUD, versions, clone/archive, assignments, responses (draft/submit), analytics, CSV/Excel/HTML(PDF) export, schema import/export, `updated_after` for mobile, field-types catalog. Permissions: `surveys:read|manage|submit`.

### Web
`/app/surveys` list with clone/archive/export; detail tabs: Builder (palette/canvas/properties), Capture, Responses, Analytics, Assignments, Versions.

### Mobile
Download published surveys, offline capture, local drafts, queued submit with retry, server-wins pull.

### Security
Org isolation on every query; audit on create/update/publish/response/assignment; RBAC enforced.

### Tests
`tests/test_surveys.py` — schema v2, validation, clone/archive, tenant isolation, idempotency, `updated_after`. Full API suite green.

---

## Known deferrals / v1.1.x polish
- True binary media upload storage (URI placeholders today)
- Native PDF binary (HTML print-to-PDF path shipped)
- Drag-and-drop reorder (up/down shipped; `@dnd-kit` optional later)
- Bulk CSV response import
- Kobo/ODK importer
- Randomization UI toggle (schema setting exists)
