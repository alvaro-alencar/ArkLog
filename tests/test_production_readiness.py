"""Regression tests for production readiness and credential architecture guardrails."""

import pytest

from app.api.v1.routes.health import _readiness_payload
from app.core.config import settings
from app.core.events import (
    _forbidden_global_credentials,
    _validate_production_config,
)


def test_readiness_payload_separates_optional_provider_debt() -> None:
    payload = _readiness_payload(
        "healthy",
        {
            "ark_auth": "configured",
            "openrouter": "configured",
            "credential_vault": "configured",
            "database": "healthy",
            "github_app": "configured",
            "slack_oauth": "configured",
            "notion_oauth": "pending",
            "clickup_oauth": "pending",
            "trello_oauth": "pending",
        },
    )

    assert payload["ready"] is True
    assert payload["providers"]["configured"] == ["github", "slack"]
    assert payload["providers"]["pending"] == ["notion", "clickup", "trello"]


def test_degraded_readiness_is_not_operable() -> None:
    payload = _readiness_payload(
        "degraded",
        {
            "ark_auth": "configured",
            "openrouter": "missing",
            "credential_vault": "configured",
            "database": "healthy",
        },
    )

    assert payload["ready"] is False


def test_legacy_global_credentials_are_detected_by_name_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "clickup_api_token", "super-secret-value")
    monkeypatch.setattr(settings, "clickup_team_id", "team-123")

    assert _forbidden_global_credentials() == [
        "CLICKUP_API_TOKEN",
        "CLICKUP_TEAM_ID",
    ]


def test_production_refuses_retired_global_provider_architecture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "clickup_api_token", "must-not-appear")
    monkeypatch.setattr(settings, "clickup_team_id", "")

    with pytest.raises(RuntimeError) as raised:
        _validate_production_config()

    message = str(raised.value)
    assert "CLICKUP_API_TOKEN" in message
    assert "must-not-appear" not in message
    assert "Connect the provider through the ArkLog user interface" in message
