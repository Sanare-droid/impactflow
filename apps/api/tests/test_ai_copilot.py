"""Epic 2 AI orchestration tests: tools, tenant scoping, citations, insights."""

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import ai_tools
from tests.conftest import auth_headers, unlock_plan_features


def test_select_tools_beneficiary_query_includes_search_beneficiaries():
    tools = ai_tools.select_tools("How many women beneficiaries did we reach?")
    assert "search_beneficiaries" in tools
    assert 1 <= len(tools) <= 5


@pytest.mark.asyncio
async def test_run_tools_is_tenant_scoped(
    client: AsyncClient, db_session: AsyncSession, org_a: dict, org_b: dict
):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/programs",
        headers=headers_a,
        json={"name": "Alpha Vaccination Program", "status": "active"},
    )
    assert created.status_code == 201, created.text

    org_a_id = UUID(org_a["organization_id"])
    org_b_id = UUID(org_b["organization_id"])

    run_a = await ai_tools.run_tools(
        db_session, org_a_id, ["search_programs"], "program", {"ai:use"}
    )
    names_a = [
        p["name"]
        for p in run_a["results"]["search_programs"]["data"]["programs"]
    ]
    assert "Alpha Vaccination Program" in names_a

    run_b = await ai_tools.run_tools(
        db_session, org_b_id, ["search_programs"], "program", {"ai:use"}
    )
    names_b = [
        p["name"]
        for p in run_b["results"]["search_programs"]["data"]["programs"]
    ]
    assert "Alpha Vaccination Program" not in names_b


@pytest.mark.asyncio
async def test_send_message_returns_citations_in_metadata(
    client: AsyncClient, org_a: dict
):
    await unlock_plan_features(client, org_a)
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])

    # Seed a program so the copilot has something to cite.
    await client.post(
        "/api/v1/programs",
        headers=headers,
        json={"name": "Nutrition Program", "status": "active"},
    )

    conv = await client.post(
        "/api/v1/ai/conversations", headers=headers, json={"title": "Test"}
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]

    sent = await client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "List our programs please"},
    )
    assert sent.status_code == 200, sent.text
    body = sent.json()
    assistant_msgs = [m for m in body["messages"] if m["role"] == "assistant"]
    assert assistant_msgs, body
    meta = assistant_msgs[-1]["metadata"]
    assert meta is not None
    assert "citations" in meta
    assert "tools_used" in meta
    assert any(c.get("type") == "program" for c in meta["citations"])


@pytest.mark.asyncio
async def test_dashboard_insights_returns_required_keys(
    client: AsyncClient, org_a: dict
):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.get("/api/v1/ai/insights/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    for key in (
        "summary",
        "key_risks",
        "key_wins",
        "recommendations",
        "upcoming_actions",
        "predictions",
        "generated_at",
    ):
        assert key in body, f"missing {key}"


@pytest.mark.asyncio
async def test_cross_tenant_conversation_access_404(
    client: AsyncClient, org_a: dict, org_b: dict
):
    await unlock_plan_features(client, org_a)
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    conv = await client.post(
        "/api/v1/ai/conversations", headers=headers_a, json={"title": "Alpha"}
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]

    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])
    denied = await client.get(
        f"/api/v1/ai/conversations/{conv_id}", headers=headers_b
    )
    assert denied.status_code == 404, denied.text


@pytest.mark.asyncio
async def test_suggested_questions_ok(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.get("/api/v1/ai/suggested-questions", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["questions"], list)
    assert len(body["questions"]) >= 1


@pytest.mark.asyncio
async def test_regenerate_does_not_duplicate_user_message(
    client: AsyncClient, org_a: dict
):
    await unlock_plan_features(client, org_a)
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    conv = await client.post(
        "/api/v1/ai/conversations", headers=headers, json={"title": "Regenerate"}
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]

    sent = await client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "How many programs do we run?"},
    )
    assert sent.status_code == 200, sent.text
    before = sent.json()
    user_before = [m for m in before["messages"] if m["role"] == "user"]
    assert len(user_before) == 1

    regenerated = await client.post(
        f"/api/v1/ai/conversations/{conv_id}/regenerate", headers=headers
    )
    assert regenerated.status_code == 200, regenerated.text
    after = regenerated.json()
    user_after = [m for m in after["messages"] if m["role"] == "user"]
    assistant_after = [m for m in after["messages"] if m["role"] == "assistant"]
    assert len(user_after) == 1, after
    assert len(assistant_after) >= 1, after


@pytest.mark.asyncio
async def test_pin_conversation(client: AsyncClient, org_a: dict):
    await unlock_plan_features(client, org_a)
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    conv = await client.post(
        "/api/v1/ai/conversations", headers=headers, json={"title": "Pin me"}
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]
    assert conv.json()["pinned"] is False

    pinned = await client.patch(
        f"/api/v1/ai/conversations/{conv_id}",
        headers=headers,
        json={"pinned": True},
    )
    assert pinned.status_code == 200, pinned.text
    assert pinned.json()["pinned"] is True

    listed = await client.get(
        "/api/v1/ai/conversations?pinned=true", headers=headers
    )
    assert listed.status_code == 200, listed.text
    ids = [c["id"] for c in listed.json()["items"]]
    assert conv_id in ids


@pytest.mark.asyncio
async def test_generate_report_returns_markdown(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    response = await client.post(
        "/api/v1/ai/reports/generate",
        headers=headers,
        json={"report_type": "monthly"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["report_type"] == "monthly"
    assert isinstance(body["content"], str)
    assert len(body["content"].strip()) > 0
    assert body["title"]


@pytest.mark.asyncio
async def test_message_feedback(client: AsyncClient, org_a: dict):
    await unlock_plan_features(client, org_a)
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    conv = await client.post(
        "/api/v1/ai/conversations", headers=headers, json={"title": "Feedback"}
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]

    sent = await client.post(
        f"/api/v1/ai/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "Give me a quick summary"},
    )
    assert sent.status_code == 200, sent.text
    assistant_msgs = [m for m in sent.json()["messages"] if m["role"] == "assistant"]
    assert assistant_msgs, sent.text
    message_id = assistant_msgs[-1]["id"]

    feedback = await client.post(
        f"/api/v1/ai/messages/{message_id}/feedback",
        headers=headers,
        json={"feedback": "up"},
    )
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["metadata"]["feedback"] == "up"
