"""Regression tests for ArkLog cost and credential isolation."""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.integrations.github.api_client import _headers
from app.models.tables import ArkLogAccessRecord
from app.security.access import public_access


def test_trial_is_closed_by_default_and_limited_to_one_report() -> None:
    assert settings.arklog_auto_trial is False
    assert settings.arklog_trial_report_limit == 1
    assert settings.ai_trial_max_tokens <= settings.ai_max_tokens
    assert settings.ai_trial_max_prompt_chars < settings.ai_max_prompt_chars


def test_public_access_never_hides_the_real_server_quota() -> None:
    access = ArkLogAccessRecord(
        user_id=1,
        status="TRIAL",
        report_limit=1,
        reports_used=1,
        is_admin=False,
    )
    assert public_access(access)["remainingReports"] == 0


def test_non_admin_github_reads_never_fall_back_to_owner_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "github_token", "owner-secret")
    assert "Authorization" not in _headers(token=None, use_global_token=False)
    assert _headers(token=None, use_global_token=True)["Authorization"] == "Bearer owner-secret"
