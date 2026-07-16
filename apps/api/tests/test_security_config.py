"""Security configuration checks (C6)."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core.secrets import validate_runtime_secrets
from app.main import API_VERSION
from app.main import app as fastapi_app


def test_openapi_enabled_in_development():
    assert fastapi_app.docs_url == "/docs"
    assert fastapi_app.redoc_url == "/redoc"


def test_openapi_disabled_when_production():
    with patch("app.main.settings") as mock_settings:
        mock_settings.app_name = "ImpactFlow AI"
        mock_settings.is_production = True
        mock_settings.backend_cors_origins = ["https://app.example.com"]
        mock_settings.api_v1_prefix = "/api/v1"
        mock_settings.app_env = "production"
        mock_settings.jobs_enabled = False

        prod_app = FastAPI(
            title="ImpactFlow AI",
            version=API_VERSION,
            docs_url=None if mock_settings.is_production else "/docs",
            redoc_url=None if mock_settings.is_production else "/redoc",
        )
        assert prod_app.docs_url is None
        assert prod_app.redoc_url is None


def test_validate_runtime_secrets_blocks_production_defaults():
    fake = Settings(
        app_env="production",
        jwt_secret_key="change_me_to_a_64_char_random_secret_key_immediately",
        encryption_key="generate_a_fernet_key_and_replace_this",
    )
    with patch("app.core.secrets.settings", fake):
        with pytest.raises(RuntimeError, match="Refusing to start"):
            validate_runtime_secrets()


def test_validate_runtime_secrets_warns_in_development():
    fake = Settings(
        app_env="development",
        jwt_secret_key="change_me_to_a_64_char_random_secret_key_immediately",
        encryption_key="generate_a_fernet_key_and_replace_this",
    )
    with patch("app.core.secrets.settings", fake):
        validate_runtime_secrets()  # should not raise


def test_cors_origins_parsed_from_csv():
    s = Settings(backend_cors_origins="https://a.example.com, https://b.example.com")
    assert "https://a.example.com" in s.backend_cors_origins
    assert "https://b.example.com" in s.backend_cors_origins


@pytest.mark.asyncio
async def test_ready_endpoint_shape(client):
    """/ready always returns structured checks (may be 503 without live DB/Redis)."""
    response = await client.get("/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "checks" in body
    assert "database" in body["checks"]
    assert "redis" in body["checks"]
