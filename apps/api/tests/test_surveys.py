import asyncio
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


def _v2_schema(required: bool = True) -> dict:
    return {
        "schema_version": 2,
        "pages": [
            {
                "id": "page_1",
                "title": "Page 1",
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "Questions",
                        "fields": [
                            {
                                "id": "hh_size",
                                "type": "number",
                                "label": "Household size",
                                "required": required,
                            },
                            {
                                "id": "notes",
                                "type": "text",
                                "label": "Notes",
                                "required": False,
                            },
                        ],
                    }
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_create_publish_and_submit_survey(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/surveys",
        headers=headers,
        json={
            "name": "Household baseline",
            "schema": {
                "fields": [
                    {"id": "hh_size", "label": "Household size", "type": "number", "required": True},
                    {"id": "notes", "label": "Notes", "type": "text"},
                ]
            },
        },
    )
    assert created.status_code == 201, created.text
    survey = created.json()
    assert survey["name"] == "Household baseline"
    assert survey["status"] == "draft"

    published = await client.patch(
        f"/api/v1/surveys/{survey['id']}",
        headers=headers,
        json={"publish": True},
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"

    detail = await client.get(f"/api/v1/surveys/{survey['id']}", headers=headers)
    assert detail.status_code == 200
    assert "hh_size" in str(detail.json()["version"]["schema"])

    submitted = await client.post(
        f"/api/v1/surveys/{survey['id']}/responses",
        headers=headers,
        json={"answers": {"hh_size": 5, "notes": "Rural"}, "respondent_name": "Amina"},
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["answers"]["hh_size"] == 5

    stats = await client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats.status_code == 200
    body = stats.json()
    assert body["surveys_count"] >= 1
    assert body["survey_responses_count"] >= 1


@pytest.mark.asyncio
async def test_field_types_and_default_schema_v2(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    types = await client.get("/api/v1/surveys/field-types", headers=headers)
    assert types.status_code == 200, types.text
    codes = {t["code"] for t in types.json()}
    assert {"text", "number", "dropdown", "gps", "multi_select"}.issubset(codes)

    created = await client.post(
        "/api/v1/surveys",
        headers=headers,
        json={"name": "Default schema survey"},
    )
    assert created.status_code == 201, created.text
    detail = await client.get(f"/api/v1/surveys/{created.json()['id']}", headers=headers)
    assert detail.json()["version"]["schema"]["schema_version"] == 2


@pytest.mark.asyncio
async def test_submit_rejects_missing_required_field(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/surveys",
        headers=headers,
        json={"name": "Strict form", "status": "published", "schema": _v2_schema(required=True)},
    )
    assert created.status_code == 201, created.text
    survey_id = created.json()["id"]

    rejected = await client.post(
        f"/api/v1/surveys/{survey_id}/responses",
        headers=headers,
        json={"answers": {}, "status": "submitted"},
    )
    assert rejected.status_code == 422, rejected.text

    accepted = await client.post(
        f"/api/v1/surveys/{survey_id}/responses",
        headers=headers,
        json={"answers": {"hh_size": 3}, "status": "submitted"},
    )
    assert accepted.status_code == 201, accepted.text


@pytest.mark.asyncio
async def test_clone_and_archive_survey(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/surveys",
        headers=headers,
        json={"name": "Clone source", "schema": _v2_schema()},
    )
    assert created.status_code == 201, created.text
    survey_id = created.json()["id"]

    cloned = await client.post(f"/api/v1/surveys/{survey_id}/clone", headers=headers)
    assert cloned.status_code == 201, cloned.text
    clone_body = cloned.json()
    assert clone_body["cloned_from_id"] == survey_id
    assert clone_body["status"] == "draft"
    assert clone_body["id"] != survey_id

    archived = await client.post(f"/api/v1/surveys/{survey_id}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_survey_tenant_isolation(client: AsyncClient, org_a: dict, org_b: dict):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])

    created = await client.post(
        "/api/v1/surveys",
        headers=headers_a,
        json={"name": "Org A only survey"},
    )
    assert created.status_code == 201, created.text
    survey_id = created.json()["id"]

    forbidden = await client.get(f"/api/v1/surveys/{survey_id}", headers=headers_b)
    assert forbidden.status_code == 404

    listing = await client.get("/api/v1/surveys", headers=headers_b)
    assert listing.status_code == 200
    assert all(item["id"] != survey_id for item in listing.json()["items"])


@pytest.mark.asyncio
async def test_response_client_mutation_id_idempotency(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/surveys",
        headers=headers,
        json={"name": "Idempotent form", "status": "published", "schema": _v2_schema(required=False)},
    )
    assert created.status_code == 201, created.text
    survey_id = created.json()["id"]

    payload = {
        "answers": {"hh_size": 4, "notes": "First submit"},
        "status": "submitted",
        "client_mutation_id": "mutation-123",
    }
    first = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    second = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=headers, json=payload)
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    listing = await client.get(
        "/api/v1/survey-responses", headers=headers, params={"survey_id": survey_id}
    )
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] == 1

    # Requests without a client_mutation_id are never deduplicated.
    third = await client.post(
        f"/api/v1/surveys/{survey_id}/responses",
        headers=headers,
        json={"answers": {"hh_size": 2}, "status": "submitted"},
    )
    assert third.status_code == 201, third.text
    listing2 = await client.get(
        "/api/v1/survey-responses", headers=headers, params={"survey_id": survey_id}
    )
    assert listing2.json()["meta"]["total"] == 2


@pytest.mark.asyncio
async def test_list_surveys_updated_after_filter(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])

    older = await client.post("/api/v1/surveys", headers=headers, json={"name": "Older survey"})
    assert older.status_code == 201, older.text

    cutoff = datetime.now(timezone.utc)
    await asyncio.sleep(0.05)

    newer = await client.post("/api/v1/surveys", headers=headers, json={"name": "Newer survey"})
    assert newer.status_code == 201, newer.text

    filtered = await client.get(
        "/api/v1/surveys",
        headers=headers,
        params={"updated_after": cutoff.isoformat()},
    )
    assert filtered.status_code == 200, filtered.text
    ids = {item["id"] for item in filtered.json()["items"]}
    assert newer.json()["id"] in ids
    assert older.json()["id"] not in ids


@pytest.mark.asyncio
async def test_survey_export_pdf_is_a_real_pdf(client: AsyncClient, org_a: dict):
    """format=pdf on the responses export must return an actual PDF binary."""
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/surveys",
        headers=headers,
        json={
            "name": "PDF export survey",
            "schema": {"fields": [{"id": "hh_size", "label": "Household size", "type": "number"}]},
        },
    )
    assert created.status_code == 201, created.text
    survey_id = created.json()["id"]
    await client.patch(f"/api/v1/surveys/{survey_id}", headers=headers, json={"publish": True})
    await client.post(
        f"/api/v1/surveys/{survey_id}/responses",
        headers=headers,
        json={"answers": {"hh_size": 4}, "status": "submitted"},
    )

    res = await client.get(
        f"/api/v1/surveys/{survey_id}/export",
        headers=headers,
        params={"format": "pdf"},
    )
    assert res.status_code == 200, res.text
    assert res.headers.get("content-type", "").startswith("application/pdf")
    assert res.content[:5] == b"%PDF-"
    cd = res.headers.get("content-disposition", "")
    assert cd.endswith('.pdf"')
    assert ".pdf.html" not in cd
