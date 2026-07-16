"""Tests for the V1.3 Epic 3 workflow automation engine."""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.services import workflows as wf
from tests.conftest import auth_headers


def _notify_definition() -> dict:
    return {
        "trigger": {"type": "beneficiary.registered"},
        "actions": [
            {
                "id": "notify",
                "type": "send_notification",
                "name": "Notify team",
                "config": {
                    "title": "New beneficiary: {{trigger.title}}",
                    "body": "A beneficiary was registered.",
                    "severity": "info",
                },
            }
        ],
    }


def _conditional_definition() -> dict:
    return {
        "trigger": {
            "type": "prediction.opened",
            "conditions": {
                "op": "and",
                "rules": [
                    {"field": "metadata.severity", "cmp": "in", "value": ["high", "critical"]}
                ],
            },
        },
        "actions": [
            {
                "id": "log",
                "type": "log_message",
                "config": {"message": "risk {{trigger.title}}"},
            }
        ],
    }


async def _create_active_workflow(
    client: AsyncClient, headers: dict, definition: dict, *, name: str = "Test WF"
) -> str:
    created = await client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": name, "definition": definition},
    )
    assert created.status_code == 201, created.text
    workflow_id = created.json()["id"]
    activated = await client.post(
        f"/api/v1/workflows/{workflow_id}/activate", headers=headers
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    return workflow_id


@pytest.mark.asyncio
async def test_create_and_activate_workflow(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Welcome flow", "definition": _notify_definition()},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["current_version"] == 1

    activated = await client.post(
        f"/api/v1/workflows/{body['id']}/activate", headers=headers
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"

    detail = await client.get(f"/api/v1/workflows/{body['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["definition"]["trigger"]["type"] == "beneficiary.registered"


@pytest.mark.asyncio
async def test_catalog_endpoints(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    for path, key in (
        ("/api/v1/workflows/triggers", "triggers"),
        ("/api/v1/workflows/actions", "actions"),
        ("/api/v1/workflows/operators", "operators"),
        ("/api/v1/workflows/templates", "templates"),
    ):
        resp = await client.get(path, headers=headers)
        assert resp.status_code == 200, resp.text
        assert len(resp.json()[key]) > 0


@pytest.mark.asyncio
async def test_matching_event_enqueues_and_executes_run(
    client: AsyncClient, db_session: AsyncSession, org_a: dict
):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    await _create_active_workflow(client, headers, _notify_definition())
    org_id = UUID(org_a["organization_id"])

    runs = await wf.enqueue_matching_runs(
        db_session,
        org_id,
        "beneficiary.registered",
        {"event": "beneficiary.registered", "title": "Jane Doe", "metadata": {}},
    )
    assert len(runs) == 1

    result = await wf.process_run_queue(db_session)
    assert result["processed"] >= 1

    run = await wf.get_run(db_session, org_id, runs[0].id)
    assert run.status == "succeeded"

    notif_count = await db_session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.organization_id == org_id)
    )
    assert notif_count >= 1


@pytest.mark.asyncio
async def test_conditions_fail_no_enqueue(
    client: AsyncClient, db_session: AsyncSession, org_a: dict
):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    await _create_active_workflow(
        client, headers, _conditional_definition(), name="Risk flow"
    )
    org_id = UUID(org_a["organization_id"])

    runs = await wf.enqueue_matching_runs(
        db_session,
        org_id,
        "prediction.opened",
        {"event": "prediction.opened", "title": "Low risk", "metadata": {"severity": "low"}},
    )
    assert runs == []

    runs_match = await wf.enqueue_matching_runs(
        db_session,
        org_id,
        "prediction.opened",
        {"event": "prediction.opened", "title": "Big risk", "metadata": {"severity": "high"}},
    )
    assert len(runs_match) == 1


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient, org_a: dict, org_b: dict):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/workflows",
        headers=headers_a,
        json={"name": "Alpha only", "definition": _notify_definition()},
    )
    assert created.status_code == 201
    workflow_id = created.json()["id"]

    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])
    cross = await client.get(f"/api/v1/workflows/{workflow_id}", headers=headers_b)
    assert cross.status_code == 404


@pytest.mark.asyncio
async def test_clone_template(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    resp = await client.post(
        "/api/v1/workflows/templates/new-beneficiary-welcome/clone", headers=headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["is_template"] is False


@pytest.mark.asyncio
async def test_manual_run_and_process_queue(
    client: AsyncClient, db_session: AsyncSession, org_a: dict
):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    workflow_id = await _create_active_workflow(client, headers, _notify_definition())

    run_resp = await client.post(
        f"/api/v1/workflows/{workflow_id}/run",
        headers=headers,
        json={"inputs": {"foo": "bar"}},
    )
    assert run_resp.status_code == 201, run_resp.text
    assert run_resp.json()["status"] == "pending"

    org_id = UUID(org_a["organization_id"])
    result = await wf.process_run_queue(db_session)
    assert result["processed"] >= 1

    run = await wf.get_run(db_session, org_id, UUID(run_resp.json()["id"]))
    assert run.status == "succeeded"


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    await _create_active_workflow(client, headers, _notify_definition())
    resp = await client.get("/api/v1/workflows/metrics", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "workflow_status_counts" in body
    assert "run_status_counts" in body
    assert "queue_depth" in body
