"""Tests for the ClickUp publisher. HTTP calls are fully mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.clickup.publisher import ClickUpPublisher

SAMPLE_PAYLOAD = {
    "project_name": "SmartEAD",
    "clickup_task_id": "task_abc123",
    "content": "Authentication infrastructure was established this period.",
    "summary": "Authentication infrastructure was established this period.",
    "commit_count": 3,
    "trigger": "webhook",
}


def _make_publisher() -> ClickUpPublisher:
    publisher = ClickUpPublisher()
    publisher._client = MagicMock()
    publisher._client.post_task_comment = AsyncMock(return_value="comment_xyz")
    return publisher


@pytest.mark.asyncio
async def test_publisher_calls_clickup_api():
    publisher = _make_publisher()
    with (
        patch.object(ClickUpPublisher, "_mark_published", new_callable=AsyncMock),
        patch("app.integrations.clickup.publisher.settings") as mock_settings,
    ):
        mock_settings.clickup_api_token = "configured-only-in-backend"
        await publisher.handle_report_generated(SAMPLE_PAYLOAD)
    publisher._client.post_task_comment.assert_awaited_once()
    call_args = publisher._client.post_task_comment.call_args
    assert call_args.args[0] == "task_abc123"


@pytest.mark.asyncio
async def test_publisher_skips_when_no_task_id():
    publisher = _make_publisher()
    await publisher.handle_report_generated({**SAMPLE_PAYLOAD, "clickup_task_id": ""})
    publisher._client.post_task_comment.assert_not_awaited()


@pytest.mark.asyncio
async def test_publisher_skips_when_no_content():
    publisher = _make_publisher()
    await publisher.handle_report_generated({**SAMPLE_PAYLOAD, "content": ""})
    publisher._client.post_task_comment.assert_not_awaited()


@pytest.mark.asyncio
async def test_publisher_skips_when_token_not_configured():
    publisher = _make_publisher()
    with patch("app.integrations.clickup.publisher.settings") as mock_settings:
        mock_settings.clickup_api_token = ""
        await publisher.handle_report_generated(SAMPLE_PAYLOAD)
    publisher._client.post_task_comment.assert_not_awaited()


def test_format_contains_project_name():
    publisher = ClickUpPublisher()
    result = publisher._format_for_clickup(SAMPLE_PAYLOAD)
    assert "SmartEAD" in result


def test_format_contains_report_content():
    publisher = ClickUpPublisher()
    result = publisher._format_for_clickup(SAMPLE_PAYLOAD)
    assert "Authentication infrastructure" in result


def test_format_scheduled_trigger_label():
    publisher = ClickUpPublisher()
    result = publisher._format_for_clickup({**SAMPLE_PAYLOAD, "trigger": "scheduled"})
    assert "scheduled checkpoint" in result
