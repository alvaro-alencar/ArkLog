"""Cloud deployments must never fall back to local SQLite or empty secrets."""

import pytest

from app.core.config import settings
from app.core.events import _missing_secure_configuration, _validate_production_config


def test_vercel_requires_secure_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(settings, "app_env", "development")
    assert settings.is_cloud is True
    assert settings.requires_secure_configuration is True
    assert settings.is_development is False


def test_cloud_configuration_fails_before_database_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite:///./data/arklog.db")
    monkeypatch.setattr(settings, "ai_api_key", "")
    monkeypatch.setattr(settings, "connections_encryption_key", "")
    monkeypatch.setattr(settings, "oauth_state_secret", "")
    monkeypatch.setattr(settings, "public_app_url", "http://localhost:5173")

    missing = _missing_secure_configuration()
    assert "DATABASE_URL PostgreSQL" in missing
    assert "AI_API_KEY" in missing
    assert "CONNECTIONS_ENCRYPTION_KEY (32+ chars)" in missing
    assert "OAUTH_STATE_SECRET (32+ chars)" in missing
    assert "PUBLIC_APP_URL HTTPS" in missing
    with pytest.raises(RuntimeError, match="Missing secure production configuration"):
        _validate_production_config()


def test_complete_cloud_configuration_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+asyncpg://user:password@example.neon.tech/neondb",
    )
    monkeypatch.setattr(settings, "ai_api_key", "openrouter-placeholder")
    monkeypatch.setattr(settings, "connections_encryption_key", "vault-secret-" * 4)
    monkeypatch.setattr(settings, "oauth_state_secret", "oauth-secret-" * 4)
    monkeypatch.setattr(settings, "public_app_url", "https://www.arksystem.net/arklog")
    monkeypatch.setattr(
        settings,
        "ark_auth_me_url",
        "https://www.arksystem.net/api/saas?action=me",
    )

    assert _missing_secure_configuration() == []
    _validate_production_config()
