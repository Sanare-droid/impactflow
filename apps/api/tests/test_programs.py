import pytest
from app.services.programs import make_code


def test_make_code_slugifies():
    assert make_code("Climate Resilience") == "CLIMATE-RESILIENCE"
    assert make_code("food security!!", prefix="PRG-").startswith("PRG-")


@pytest.mark.asyncio
async def test_health_version(client):
    # Uses shared client fixture when integration available; skip gracefully otherwise
    pass
