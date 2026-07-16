"""Mailer provider selection tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services import mailer


@pytest.mark.asyncio
async def test_send_email_uses_resend_when_api_key_set():
    fake = Settings(
        resend_api_key="re_test_key",
        smtp_from="ImpactFlow <onboarding@resend.dev>",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"id":"msg_1"}'
    mock_response.json.return_value = {"id": "msg_1"}
    mock_response.text = ""

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_response

    with (
        patch("app.services.mailer.settings", fake),
        patch("app.services.mailer.httpx.AsyncClient", return_value=mock_client),
    ):
        result = await mailer.send_email(
            to="user@example.com",
            subject="Hello",
            body="Test body",
        )

    assert result["status"] == "sent"
    assert result["provider"] == "resend"
    assert result["id"] == "msg_1"
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.await_args
    assert args[0] == "https://api.resend.com/emails"
    assert kwargs["json"]["to"] == ["user@example.com"]


@pytest.mark.asyncio
async def test_send_email_falls_back_to_stub_without_providers():
    fake = Settings(resend_api_key="", smtp_host="")
    with patch("app.services.mailer.settings", fake):
        result = await mailer.send_email(
            to="user@example.com",
            subject="Hello",
            body="Test body",
        )
    assert result["status"] == "queued_stub"
    assert result["provider"] == "log"
