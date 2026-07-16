"""Connector registry — plug-in catalog without modifying core modules.

Each connector declares auth, sync capabilities, and config schema.
Runtime handlers live in ``services.connectors.runtime``.
"""

from __future__ import annotations

from typing import Any, Optional

CONNECTOR_CATALOG: list[dict[str, Any]] = [
    # Productivity
    {
        "code": "microsoft-365",
        "name": "Microsoft 365",
        "category": "productivity",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Calendar, OneDrive, and Teams file sync via Microsoft Graph.",
        "config_schema": {
            "fields": [
                {"key": "tenant_id", "label": "Azure Tenant ID", "required": True},
                {"key": "client_id", "label": "App Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
            ]
        },
        "oauth": {
            "authorize_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            "scopes": ["Files.ReadWrite.All", "User.Read", "offline_access"],
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "google-workspace",
        "name": "Google Workspace",
        "category": "productivity",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Drive, Sheets, and Calendar via Google APIs.",
        "config_schema": {
            "fields": [
                {"key": "client_id", "label": "OAuth Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
            ]
        },
        "oauth": {
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "google-drive",
        "name": "Google Drive",
        "category": "productivity",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Evidence and report file sync with Google Drive.",
        "config_schema": {
            "fields": [
                {"key": "client_id", "label": "OAuth Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
                {"key": "folder_id", "label": "Root Folder ID", "required": False},
            ]
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "onedrive",
        "name": "OneDrive",
        "category": "productivity",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Sync documents and evidence with OneDrive / SharePoint.",
        "config_schema": {
            "fields": [
                {"key": "tenant_id", "label": "Tenant ID", "required": True},
                {"key": "client_id", "label": "Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "dropbox",
        "name": "Dropbox",
        "category": "productivity",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "File sync with Dropbox Business.",
        "config_schema": {
            "fields": [
                {"key": "app_key", "label": "App Key", "required": True},
                {"key": "app_secret", "label": "App Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "box",
        "name": "Box",
        "category": "productivity",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Enterprise content sync with Box.",
        "config_schema": {
            "fields": [
                {"key": "client_id", "label": "Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    # Data collection
    {
        "code": "kobo",
        "name": "KoboToolbox",
        "category": "data_collection",
        "auth_type": "api_key",
        "sync_modes": ["pull"],
        "directions": ["inbound"],
        "description": "Pull form submissions into surveys and monitoring.",
        "config_schema": {
            "fields": [
                {"key": "server_url", "label": "Server URL", "required": True},
                {"key": "token", "label": "API Token", "secret": True, "required": True},
                {"key": "asset_uid", "label": "Asset UID", "required": False},
            ]
        },
        "health_check": "http_get",
        "health_path": "/api/v2/assets.json",
        "version": "1.0.0",
        "marketplace_code": "kobo-connector",
    },
    {
        "code": "odk-central",
        "name": "ODK Central",
        "category": "data_collection",
        "auth_type": "bearer",
        "sync_modes": ["pull"],
        "directions": ["inbound"],
        "description": "Ingest ODK Central submissions for field monitoring.",
        "config_schema": {
            "fields": [
                {"key": "base_url", "label": "Base URL", "required": True},
                {"key": "email", "label": "Email", "required": True},
                {"key": "password", "label": "Password", "secret": True, "required": True},
                {"key": "project_id", "label": "Project ID", "required": True},
            ]
        },
        "health_check": "http_get",
        "health_path": "/v1/projects",
        "version": "1.0.0",
        "marketplace_code": "odk-central",
    },
    {
        "code": "surveycto",
        "name": "SurveyCTO",
        "category": "data_collection",
        "auth_type": "api_key",
        "sync_modes": ["pull"],
        "directions": ["inbound"],
        "description": "Sync SurveyCTO form data into ImpactFlow surveys.",
        "config_schema": {
            "fields": [
                {"key": "server", "label": "Server", "required": True},
                {"key": "username", "label": "Username", "required": True},
                {"key": "password", "label": "Password", "secret": True, "required": True},
            ]
        },
        "health_check": "config",
        "version": "1.0.0",
    },
    # GIS
    {
        "code": "arcgis",
        "name": "ArcGIS",
        "category": "gis",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Sync map layers and community features with ArcGIS Online.",
        "config_schema": {
            "fields": [
                {"key": "portal_url", "label": "Portal URL", "required": True},
                {"key": "client_id", "label": "Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "geojson-export",
        "name": "GeoJSON Export",
        "category": "gis",
        "auth_type": "none",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Export communities and map features as GeoJSON.",
        "config_schema": {"fields": [{"key": "include_households", "label": "Include households", "type": "boolean"}]},
        "health_check": "config",
        "version": "1.0.0",
    },
    {
        "code": "shapefile-export",
        "name": "Shapefile Export",
        "category": "gis",
        "auth_type": "none",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Export geospatial layers for QGIS / ArcGIS Desktop.",
        "config_schema": {"fields": []},
        "health_check": "config",
        "version": "1.0.0",
    },
    {
        "code": "qgis-export",
        "name": "QGIS Export",
        "category": "gis",
        "auth_type": "none",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Package project GeoPackage for QGIS.",
        "config_schema": {"fields": []},
        "health_check": "config",
        "version": "1.0.0",
    },
    # Communication
    {
        "code": "slack",
        "name": "Slack",
        "category": "communication",
        "auth_type": "webhook_secret",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Push alerts and workflow notifications to Slack.",
        "config_schema": {
            "fields": [
                {"key": "webhook_url", "label": "Incoming Webhook URL", "secret": True, "required": True},
                {"key": "channel", "label": "Default Channel", "required": False},
            ]
        },
        "health_check": "webhook_ping",
        "version": "1.0.0",
        "marketplace_code": "slack-alerts",
    },
    {
        "code": "microsoft-teams",
        "name": "Microsoft Teams",
        "category": "communication",
        "auth_type": "webhook_secret",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Post Adaptive Card alerts to Teams channels.",
        "config_schema": {
            "fields": [
                {"key": "webhook_url", "label": "Incoming Webhook URL", "secret": True, "required": True},
            ]
        },
        "health_check": "webhook_ping",
        "version": "1.0.0",
    },
    {
        "code": "email",
        "name": "Email",
        "category": "communication",
        "auth_type": "api_key",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Route notifications via org SMTP / Resend.",
        "config_schema": {
            "fields": [
                {"key": "from_address", "label": "From Address", "required": True},
                {"key": "reply_to", "label": "Reply-To", "required": False},
            ]
        },
        "health_check": "config",
        "version": "1.0.0",
    },
    {
        "code": "twilio-sms",
        "name": "Twilio SMS",
        "category": "communication",
        "auth_type": "api_key",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Future-ready SMS delivery via Twilio.",
        "config_schema": {
            "fields": [
                {"key": "account_sid", "label": "Account SID", "required": True},
                {"key": "auth_token", "label": "Auth Token", "secret": True, "required": True},
                {"key": "from_number", "label": "From Number", "required": True},
            ]
        },
        "health_check": "config",
        "status": "future_ready",
        "version": "0.1.0",
    },
    {
        "code": "whatsapp-business",
        "name": "WhatsApp Business",
        "category": "communication",
        "auth_type": "api_key",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Future-ready WhatsApp Business messaging.",
        "config_schema": {
            "fields": [
                {"key": "phone_number_id", "label": "Phone Number ID", "required": True},
                {"key": "access_token", "label": "Access Token", "secret": True, "required": True},
            ]
        },
        "health_check": "config",
        "status": "future_ready",
        "version": "0.1.0",
    },
    # Finance
    {
        "code": "quickbooks",
        "name": "QuickBooks Online",
        "category": "finance",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Sync expenses and grant spend with QuickBooks Online.",
        "config_schema": {
            "fields": [
                {"key": "client_id", "label": "Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
                {"key": "realm_id", "label": "Company Realm ID", "required": False},
            ]
        },
        "oauth": {
            "authorize_url": "https://appcenter.intuit.com/connect/oauth2",
            "token_url": "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
            "scopes": ["com.intuit.quickbooks.accounting"],
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "xero",
        "name": "Xero",
        "category": "finance",
        "auth_type": "oauth2",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Future-ready Xero accounting sync.",
        "config_schema": {
            "fields": [
                {"key": "client_id", "label": "Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "oauth_token",
        "status": "future_ready",
        "version": "0.1.0",
    },
    {
        "code": "csv-accounting",
        "name": "CSV Accounting Export",
        "category": "finance",
        "auth_type": "none",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Export finance transactions as CSV for any ledger.",
        "config_schema": {"fields": []},
        "health_check": "config",
        "version": "1.0.0",
    },
    # BI
    {
        "code": "power-bi",
        "name": "Power BI",
        "category": "bi",
        "auth_type": "oauth2",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Push datasets to Power BI for executive dashboards.",
        "config_schema": {
            "fields": [
                {"key": "workspace_id", "label": "Workspace ID", "required": True},
                {"key": "client_id", "label": "Client ID", "required": True},
                {"key": "client_secret", "label": "Client Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "oauth_token",
        "version": "1.0.0",
    },
    {
        "code": "looker-studio",
        "name": "Looker Studio",
        "category": "bi",
        "auth_type": "none",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "CSV / Sheets feed for Looker Studio.",
        "config_schema": {"fields": [{"key": "spreadsheet_id", "label": "Google Sheet ID"}]},
        "health_check": "config",
        "version": "1.0.0",
    },
    {
        "code": "tableau",
        "name": "Tableau",
        "category": "bi",
        "auth_type": "api_key",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Publish Hyper extracts / CSV to Tableau Server.",
        "config_schema": {
            "fields": [
                {"key": "server_url", "label": "Server URL", "required": True},
                {"key": "token_name", "label": "PAT Name", "required": True},
                {"key": "token_secret", "label": "PAT Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "config",
        "version": "1.0.0",
    },
    {
        "code": "csv-analytics",
        "name": "CSV Analytics Export",
        "category": "bi",
        "auth_type": "none",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Export portfolio analytics as CSV.",
        "config_schema": {"fields": []},
        "health_check": "config",
        "version": "1.0.0",
    },
    # Development
    {
        "code": "rest-api",
        "name": "REST API",
        "category": "development",
        "auth_type": "api_key",
        "sync_modes": ["pull", "push"],
        "directions": ["bidirectional"],
        "description": "Use ImpactFlow REST API with scoped organization keys.",
        "config_schema": {"fields": []},
        "health_check": "config",
        "version": "1.0.0",
    },
    {
        "code": "webhook-consumer",
        "name": "Webhook Consumer",
        "category": "development",
        "auth_type": "webhook_secret",
        "sync_modes": ["pull"],
        "directions": ["inbound"],
        "description": "Receive inbound webhooks into the event bus.",
        "config_schema": {
            "fields": [
                {"key": "path_token", "label": "Path Token", "required": True},
                {"key": "shared_secret", "label": "Shared Secret", "secret": True, "required": True},
            ]
        },
        "health_check": "config",
        "version": "1.0.0",
    },
    {
        "code": "webhook-producer",
        "name": "Webhook Producer",
        "category": "development",
        "auth_type": "webhook_secret",
        "sync_modes": ["push"],
        "directions": ["outbound"],
        "description": "Deliver signed outbound webhooks to your systems.",
        "config_schema": {
            "fields": [
                {"key": "endpoint_url", "label": "Endpoint URL", "required": True},
                {"key": "shared_secret", "label": "Signing Secret", "secret": True, "required": False},
            ]
        },
        "health_check": "webhook_ping",
        "version": "1.0.0",
    },
    {
        "code": "openapi",
        "name": "OpenAPI Documentation",
        "category": "development",
        "auth_type": "none",
        "sync_modes": [],
        "directions": ["outbound"],
        "description": "Download the live OpenAPI specification.",
        "config_schema": {"fields": []},
        "health_check": "config",
        "version": "1.0.0",
    },
]


def get_connector(code: str) -> Optional[dict[str, Any]]:
    return next((c for c in CONNECTOR_CATALOG if c["code"] == code), None)


def list_connectors(
    *,
    category: Optional[str] = None,
    include_future: bool = True,
) -> list[dict[str, Any]]:
    items = CONNECTOR_CATALOG
    if category:
        items = [c for c in items if c["category"] == category]
    if not include_future:
        items = [c for c in items if c.get("status") != "future_ready"]
    return list(items)


def connectors_by_category() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for c in CONNECTOR_CATALOG:
        out.setdefault(c["category"], []).append(c)
    return out
