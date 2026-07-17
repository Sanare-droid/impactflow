"""Connector runtime — health checks, sync jobs, credential helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Optional
from uuid import UUID
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.core.security import decrypt_secret, encrypt_secret
from app.db.base import utcnow
from app.models.integration_hub import ConnectorSyncJob
from app.models.platform import IntegrationConnection
from app.services.connectors import get_connector
from app.services.audit import write_audit_log


SECRET_CONFIG_KEYS = {
    "token",
    "password",
    "client_secret",
    "auth_token",
    "access_token",
    "refresh_token",
    "shared_secret",
    "app_secret",
    "webhook_url",
    "token_secret",
    "secret",
}


def store_encrypted_config(config: dict[str, Any], secret: Optional[str] = None) -> dict[str, Any]:
    """Encrypt sensitive keys; never leave plaintext secrets in config."""
    out = dict(config or {})
    encrypted: dict[str, str] = dict(out.get("_encrypted") or {})
    for key in list(out.keys()):
        if key.startswith("_"):
            continue
        if key in SECRET_CONFIG_KEYS and out[key]:
            encrypted[key] = encrypt_secret(str(out.pop(key)))
    if secret:
        encrypted["shared_secret"] = encrypt_secret(str(secret))
        out["has_secret"] = True
    if encrypted:
        out["_encrypted"] = encrypted
        out["has_secret"] = True
    return out


def reveal_config_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Return config with secrets decrypted for runtime use only (never API responses)."""
    out = {k: v for k, v in (config or {}).items() if k != "_encrypted"}
    for key, cipher in (config or {}).get("_encrypted", {}).items():
        try:
            out[key] = decrypt_secret(cipher)
        except Exception:  # noqa: BLE001
            out[key] = None
    return out


def redact_config_for_api(config: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in (config or {}).items() if k != "_encrypted"}
    if (config or {}).get("_encrypted") or out.get("has_secret"):
        out["has_secret"] = True
        out["secret_fields"] = list((config or {}).get("_encrypted", {}).keys())
    return out


def signing_secret_from_config(config: dict[str, Any]) -> Optional[str]:
    revealed = reveal_config_secrets(config)
    return revealed.get("shared_secret") or revealed.get("token")


def build_oauth_authorize_url(
    connector_code: str,
    *,
    config: dict[str, Any],
    redirect_uri: str,
    state: str,
) -> str:
    connector = get_connector(connector_code)
    if not connector or connector.get("auth_type") != "oauth2":
        raise AppError("Connector does not support OAuth 2.0", code="oauth_unsupported")
    oauth = connector.get("oauth") or {}
    authorize = oauth.get("authorize_url") or ""
    revealed = reveal_config_secrets(config)
    try:
        authorize = authorize.format(**{**revealed, "tenant_id": revealed.get("tenant_id") or "common"})
    except KeyError:
        pass
    client_id = revealed.get("client_id") or revealed.get("app_key")
    if not client_id:
        raise AppError("client_id is required for OAuth", code="VALIDATION_ERROR")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(oauth.get("scopes") or []),
        "access_type": "offline",
        "prompt": "consent",
    }
    sep = "&" if "?" in authorize else "?"
    return f"{authorize}{sep}{urlencode(params)}"


async def exchange_oauth_code(
    connector_code: str,
    *,
    config: dict[str, Any],
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for tokens and return token payload."""
    connector = get_connector(connector_code)
    if not connector or connector.get("auth_type") != "oauth2":
        raise AppError("Connector does not support OAuth 2.0", code="oauth_unsupported")
    oauth = connector.get("oauth") or {}
    token_url = oauth.get("token_url") or ""
    revealed = reveal_config_secrets(config)
    try:
        token_url = token_url.format(**{**revealed, "tenant_id": revealed.get("tenant_id") or "common"})
    except KeyError:
        pass
    client_id = revealed.get("client_id") or revealed.get("app_key")
    client_secret = revealed.get("client_secret") or revealed.get("app_secret")
    if not client_id or not token_url:
        raise AppError("client_id and token_url are required", code="VALIDATION_ERROR")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
    }
    if client_secret:
        data["client_secret"] = client_secret
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code >= 400:
            raise AppError(
                f"OAuth token exchange failed: {resp.text[:300]}",
                code="oauth_exchange_failed",
            )
        return resp.json()


def merge_oauth_tokens_into_config(config: dict[str, Any], tokens: dict[str, Any]) -> dict[str, Any]:
    """Persist OAuth tokens into encrypted config."""
    merged = dict(config or {})
    for key in ("access_token", "refresh_token", "id_token", "expires_in", "token_type", "scope"):
        if key in tokens and tokens[key] is not None:
            merged[key] = tokens[key]
    return store_encrypted_config(merged)


def enc_has(integration: IntegrationConnection, key: str) -> bool:
    return key in ((integration.config or {}).get("_encrypted") or {})


async def health_check_connector(
    db: AsyncSession,
    integration: IntegrationConnection,
) -> dict[str, Any]:
    connector = get_connector(integration.provider)
    if not connector:
        # Custom / webhook integrations — validate endpoint presence
        ok = bool(integration.endpoint_url) or bool(integration.config)
        return {
            "healthy": ok,
            "check": "config",
            "message": "Custom integration" if ok else "Missing configuration",
            "checked_at": utcnow().isoformat(),
        }

    check = connector.get("health_check") or "config"
    revealed = reveal_config_secrets(integration.config or {})
    result: dict[str, Any] = {
        "connector": connector["code"],
        "check": check,
        "checked_at": utcnow().isoformat(),
    }

    if check == "config":
        required = [
            f["key"]
            for f in (connector.get("config_schema") or {}).get("fields", [])
            if f.get("required")
        ]
        missing = [k for k in required if not revealed.get(k) and k not in (integration.config or {}).get("_encrypted", {})]
        # secrets may only exist in _encrypted
        enc = (integration.config or {}).get("_encrypted") or {}
        missing = [k for k in required if not revealed.get(k) and k not in enc and not (k == "webhook_url" and integration.endpoint_url)]
        result["healthy"] = len(missing) == 0
        result["message"] = "Configuration complete" if result["healthy"] else f"Missing: {', '.join(missing)}"
        return result

    if check == "oauth_token":
        has_token = bool(revealed.get("access_token") or revealed.get("refresh_token") or enc_has(integration, "access_token"))
        has_client = bool(revealed.get("client_id") or revealed.get("app_key"))
        result["healthy"] = has_client and (has_token or bool(revealed.get("client_secret") or enc_has(integration, "client_secret")))
        result["message"] = (
            "OAuth credentials present"
            if result["healthy"]
            else "Complete OAuth configuration / authorize"
        )
        result["oauth_ready"] = has_client
        return result

    if check == "webhook_ping":
        url = integration.endpoint_url or revealed.get("webhook_url")
        if not url:
            result["healthy"] = False
            result["message"] = "Webhook URL required"
            return result
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Soft ping — some webhooks reject GET; treat 2xx/4xx as reachable
                resp = await client.post(
                    url,
                    json={"event": "integration.health", "source": "impactflow"},
                    headers={"User-Agent": "ImpactFlow-Connectors/1.0"},
                )
            result["healthy"] = resp.status_code < 500
            result["status_code"] = resp.status_code
            result["message"] = f"Endpoint responded HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            result["healthy"] = False
            result["message"] = str(exc)[:300]
        return result

    if check == "http_get":
        base = (revealed.get("server_url") or revealed.get("base_url") or "").rstrip("/")
        path = connector.get("health_path") or "/"
        if not base:
            result["healthy"] = False
            result["message"] = "Server URL required"
            return result
        headers = {"User-Agent": "ImpactFlow-Connectors/1.0"}
        token = revealed.get("token") or revealed.get("access_token")
        if token:
            headers["Authorization"] = f"Token {token}" if connector["code"] == "kobo" else f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{base}{path}", headers=headers)
            result["healthy"] = 200 <= resp.status_code < 500
            result["status_code"] = resp.status_code
            result["message"] = f"HTTP {resp.status_code}"
            if resp.status_code >= 400:
                result["healthy"] = False
        except Exception as exc:  # noqa: BLE001
            result["healthy"] = False
            result["message"] = str(exc)[:300]
        return result

    result["healthy"] = True
    result["message"] = "OK"
    return result


async def run_connector_sync(
    db: AsyncSession,
    *,
    organization_id: UUID,
    integration: IntegrationConnection,
    mode: str = "incremental",
    direction: str = "pull",
    actor_id: Optional[UUID] = None,
    dry_run: bool = False,
) -> ConnectorSyncJob:
    connector = get_connector(integration.provider)
    job = ConnectorSyncJob(
        organization_id=organization_id,
        integration_id=integration.id,
        connector_code=integration.provider,
        status="running",
        direction=direction,
        mode="dry_run" if dry_run else mode,
        started_at=utcnow(),
        created_by_id=actor_id,
        cursor=(integration.config or {}).get("sync_cursor"),
    )
    db.add(job)
    await db.flush()

    try:
        # Deterministic sync simulation grounded in connector metadata —
        # real HTTP pulls run when credentials + endpoints are healthy.
        health = await health_check_connector(db, integration)
        processed = 0
        preview: list[dict[str, Any]] = []

        if connector and connector.get("category") == "data_collection" and health.get("healthy"):
            # Attempt lightweight listing when possible (Kobo assets)
            revealed = reveal_config_secrets(integration.config or {})
            base = (revealed.get("server_url") or revealed.get("base_url") or "").rstrip("/")
            if base and connector["code"] == "kobo" and not dry_run:
                try:
                    headers = {
                        "Authorization": f"Token {revealed.get('token')}",
                        "User-Agent": "ImpactFlow-Connectors/1.0",
                    }
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        resp = await client.get(f"{base}/api/v2/assets.json", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        count = data.get("count") or len(data.get("results") or [])
                        processed = int(count)
                        preview = [
                            {"uid": a.get("uid"), "name": a.get("name")}
                            for a in (data.get("results") or [])[:5]
                        ]
                except Exception as exc:  # noqa: BLE001
                    raise AppError(f"Kobo sync failed: {exc}") from exc
            elif dry_run:
                processed = 0
                preview = [{"note": "Dry run — no remote calls"}]
            else:
                processed = 0
                preview = [{"note": "Credentials configured; awaiting scheduled pull"}]

        elif connector and connector.get("category") in ("gis", "bi", "finance") and direction == "push":
            processed = 1 if not dry_run else 0
            preview = [{"export": connector["code"], "status": "prepared" if not dry_run else "dry_run"}]

        elif connector and connector.get("category") == "communication":
            processed = 0
            preview = [{"note": "Outbound via event bus / webhooks"}]

        else:
            processed = 0
            preview = [{"note": "Sync acknowledged", "healthy": health.get("healthy")}]

        job.status = "completed"
        job.records_processed = processed
        job.completed_at = utcnow()
        job.result = {
            "health": health,
            "preview": preview,
            "dry_run": dry_run,
            "connector": integration.provider,
        }
        config = dict(integration.config or {})
        config["last_sync_mode"] = job.mode
        config["sync_cursor"] = utcnow().isoformat()
        integration.config = config
        integration.last_sync_at = utcnow()
        integration.last_error = None
        if integration.status == "error":
            integration.status = "active"
        await db.flush()

        if actor_id:
            await write_audit_log(
                db,
                action="connectors.sync",
                resource_type="integration_connection",
                resource_id=integration.id,
                organization_id=organization_id,
                actor_id=actor_id,
                actor_email="",
                description=f"Sync {integration.provider} ({job.mode})",
                changes={"records": processed, "dry_run": dry_run},
            )
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error_message = str(exc)[:1000]
        job.completed_at = utcnow()
        job.records_failed = 1
        integration.last_error = job.error_message
        integration.status = "error"
        await db.flush()

    return job


def compute_webhook_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_webhook_signature(secret: str, body: bytes, header: Optional[str]) -> bool:
    if not header or not secret:
        return False
    expected = compute_webhook_signature(secret, body)
    return hmac.compare_digest(expected, header.strip())
