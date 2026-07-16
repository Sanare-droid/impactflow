import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


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
