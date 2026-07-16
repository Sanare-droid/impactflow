"""ImpactFlow Extension / Plugin SDK — register capabilities without modifying core.

Plugins declare a manifest. The platform loads routes, nav, workflow actions,
AI tools, and events through the Integrations Hub plugin_manifests table and
marketplace installs. Third-party publishers never patch core modules.
"""

from __future__ import annotations

from typing import Any

PLUGIN_SDK_VERSION = "1.0.0"

PLUGIN_SDK_MANIFEST: dict[str, Any] = {
    "sdk_version": PLUGIN_SDK_VERSION,
    "registration_points": [
        "routes",
        "navigation",
        "pages",
        "cards",
        "dashboards",
        "workflow_actions",
        "workflow_triggers",
        "reports",
        "surveys",
        "ai_tools",
        "events",
        "menus",
        "permissions",
        "api_endpoints",
    ],
    "rules": [
        "Plugins must never modify core application code.",
        "All data access must be tenant-scoped via organization_id.",
        "Secrets must use platform encrypt_secret helpers.",
        "Permissions must be declared and granted via RBAC.",
        "Marketplace installs may auto-enable matching connectors.",
    ],
    "example_manifest": {
        "code": "example-donor-widget",
        "name": "Donor Widget Pack",
        "version": "1.0.0",
        "routes": [{"path": "/plugins/donor-widget", "method": "GET"}],
        "ui_panels": ["donor_summary_card"],
        "workflow_actions": ["notify_donor"],
        "ai_tools": ["summarize_grant"],
        "events": ["grant.updated"],
        "marketplace_app_code": "donor-portal-pack",
    },
}


class PluginBuilder:
    """Fluent helper for constructing a plugin manifest dict."""

    def __init__(self, code: str, name: str, version: str = "1.0.0") -> None:
        self._manifest: dict[str, Any] = {
            "code": code,
            "name": name,
            "version": version,
            "routes": [],
            "events": [],
            "ui_panels": [],
            "workflow_actions": [],
            "ai_tools": [],
            "reports": [],
            "dashboards": [],
            "mobile_features": [],
            "marketplace_app_code": None,
            "description": None,
            "metadata": {},
        }

    def description(self, text: str) -> "PluginBuilder":
        self._manifest["description"] = text
        return self

    def marketplace(self, app_code: str) -> "PluginBuilder":
        self._manifest["marketplace_app_code"] = app_code
        return self

    def route(self, path: str, method: str = "GET") -> "PluginBuilder":
        self._manifest["routes"].append({"path": path, "method": method})
        return self

    def panel(self, panel_id: str) -> "PluginBuilder":
        self._manifest["ui_panels"].append(panel_id)
        return self

    def workflow_action(self, action: str) -> "PluginBuilder":
        self._manifest["workflow_actions"].append(action)
        return self

    def ai_tool(self, tool: str) -> "PluginBuilder":
        self._manifest["ai_tools"].append(tool)
        return self

    def event(self, event_type: str) -> "PluginBuilder":
        self._manifest["events"].append(event_type)
        return self

    def build(self) -> dict[str, Any]:
        return dict(self._manifest)


_REGISTRY: dict[str, dict[str, Any]] = {}


def register_plugin(manifest: dict[str, Any]) -> dict[str, Any]:
    """Register an in-process plugin manifest (tests / local extensions)."""
    code = manifest.get("code")
    if not code:
        raise ValueError("Plugin manifest requires code")
    _REGISTRY[code] = manifest
    return manifest


def registered_plugins() -> list[dict[str, Any]]:
    return list(_REGISTRY.values())


def clear_registry() -> None:
    _REGISTRY.clear()
