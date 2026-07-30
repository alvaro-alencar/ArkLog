"""Regression tests for safe Slack provider errors."""

from app.integrations.slack_errors import publication_error_message


def test_not_in_channel_explains_how_to_invite_the_bot() -> None:
    message = publication_error_message("not_in_channel")
    assert "/invite @ArkLog" in message
    assert "não participa" in message


def test_unknown_slack_error_remains_safe_and_actionable() -> None:
    message = publication_error_message("temporary_provider_failure")
    assert "temporary_provider_failure" in message
    assert "Slack" in message
