"""Slack channels must explain membership and source-scope requirements."""

import httpx
import pytest
import respx

from app.core.config import settings
from app.integrations.providers import slack


@pytest.mark.asyncio
@respx.mock
async def test_destination_channel_without_bot_is_unavailable() -> None:
    respx.get(f"{settings.slack_api_base_url}/conversations.list").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "channels": [
                    {
                        "id": "C123",
                        "name": "relatorios",
                        "is_private": False,
                        "is_member": False,
                    }
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )
    )

    resources = await slack.list_resources(
        {"bot_token": "xoxb-test", "_scopes": ["channels:read", "chat:write"]},
        "destination",
    )

    assert resources[0]["available"] is False
    assert "/invite @ArkLog" not in resources[0]["availabilityReason"]
    assert "Convide @ArkLog" in resources[0]["availabilityReason"]


@pytest.mark.asyncio
@respx.mock
async def test_source_channel_requires_membership_and_history_scope() -> None:
    respx.get(f"{settings.slack_api_base_url}/conversations.list").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "channels": [
                    {
                        "id": "C123",
                        "name": "produto",
                        "is_private": False,
                        "is_member": True,
                    }
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )
    )

    unavailable = await slack.list_resources(
        {"bot_token": "xoxb-test", "_scopes": ["channels:read", "chat:write"]},
        "source",
    )
    available = await slack.list_resources(
        {
            "bot_token": "xoxb-test",
            "_scopes": ["channels:read", "channels:history", "chat:write"],
        },
        "source",
    )

    assert unavailable[0]["available"] is False
    assert "Reconecte" in unavailable[0]["availabilityReason"]
    assert available[0]["available"] is True
