import pytest
from httpx import AsyncClient

from app.services.programs import make_code
from tests.conftest import auth_headers


def test_make_code_slugifies():
    assert make_code("Climate Resilience") == "CLIMATE-RESILIENCE"
    assert make_code("food security!!", prefix="PRG-").startswith("PRG-")


@pytest.mark.asyncio
async def test_health_version(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"].startswith("0.")


@pytest.mark.asyncio
async def test_create_and_list_program(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={"name": "Food Security", "status": "active"},
    )
    assert created.status_code == 201, created.text
    program = created.json()
    assert program["name"] == "Food Security"
    assert program["organization_id"] == org_a["organization_id"]

    listed = await client.get("/api/v1/programs", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] >= 1
    assert any(p["id"] == program["id"] for p in listed.json()["items"])
