# Epic 5 — Donor Intelligence, Executive Analytics & Smart Reporting

**API version:** 0.17.0 · **Migration:** `0016_phase16`

## Architecture (extends, does not rewrite)

| Layer | Approach |
|-------|----------|
| **Reporting (Phase 6)** | Extended with templates, versions, approve/publish, multi-format export |
| **AI Copilot (Epic 2)** | Reused `ai.generate_report` / `ai_intelligence` for narratives & risk — no new AI stack |
| **Workflow Engine (Epic 3)** | Existing `generate_ai_report` / `report.published` hooks still apply |
| **Notifications** | Publish still emits `report.published` via `insights.update_report` |
| **Field Ops (Epic 4)** | Field metrics surface on executive dashboard |

## Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/executive/dashboard` | Portfolio health, KPIs, risks, AI insights |
| GET | `/executive/portfolio` | Filterable analytics + chart series |
| GET | `/executive/impact` | Outputs/outcomes, cost per beneficiary |
| GET | `/executive/compliance` | Gaps, deadlines, recommendations |
| GET | `/executive/risks` | Enriched risk intelligence |
| POST | `/executive/briefs` | One-click executive brief → Report |
| GET | `/report-templates` | System + org templates |
| POST | `/report-templates/clone` | Clone USAID/EU/WB/UN/etc. |
| POST | `/reports/build` | Template + AI narrative → draft Report |
| POST | `/reports/{id}/versions` | Snapshot revision |
| POST | `/reports/{id}/approve` \| `/publish` | Lifecycle |
| GET | `/reports/{id}/export/download` | md, html, pdf.html, csv, xlsx, docx, pptx |

## Web

- `/app/executive` — executive dashboard
- `/app/reports` — template gallery, builder, exports

## Delivered (Definition of Done)

- [x] Executive dashboard with portfolio health + KPIs
- [x] AI donor narratives grounded in platform data (existing AI)
- [x] Reusable report templates (9 built-ins) + clone
- [x] Portfolio analytics with chart series
- [x] Compliance dashboard with auto-flagged gaps
- [x] Risk intelligence (extends deterministic scan)
- [x] Report versioning + approve/publish
- [x] Exports: Markdown, HTML, PDF(print HTML), CSV, Excel XML, DOCX, PPTX
- [x] Existing AI / Reporting / Workflow / Notifications reused
- [x] Tenant isolation + RBAC tests
- [x] API **0.17.0** · migration **0016**

## Deferred

- Native binary PDF engine (WeasyPrint/Chromium)
- Full GIS map charts
- Department/field-officer performance drill-down UI
- Saved executive filter views persistence
