# ImpactFlow Plugin / Extension SDK

Plugins extend ImpactFlow **without modifying core code**.

## Principles

1. Declare a **manifest** — never patch application modules.
2. All data access is **tenant-scoped** (`organization_id`).
3. Secrets use platform `encrypt_secret`.
4. Permissions are declared and granted via RBAC.
5. Marketplace installs may auto-enable matching connectors (`marketplace_code`).

## Registration points

`routes` · `navigation` · `pages` · `cards` · `dashboards` · `workflow_actions` · `workflow_triggers` · `reports` · `surveys` · `ai_tools` · `events` · `menus` · `permissions` · `api_endpoints`

## Python helper

```python
from app.plugins import PluginBuilder, register_plugin

manifest = (
    PluginBuilder("example-donor-widget", "Donor Widget Pack")
    .description("Adds a donor summary card")
    .marketplace("donor-portal-pack")
    .panel("donor_summary_card")
    .workflow_action("notify_donor")
    .ai_tool("summarize_grant")
    .event("grant.updated")
    .build()
)
register_plugin(manifest)
```

## Persistence

Production plugins are stored in `plugin_manifests` (Epic 6) and linked via `marketplace_app_code`.

## API

`GET /api/v1/plugin-sdk/manifest` — SDK contract for developers.

## Rules for publishers

- Do not import or monkey-patch core route modules.
- Prefer hub connectors for external I/O.
- Version manifests (`code` + `version` unique).
- Ship uninstall/disable paths through marketplace installation status.
