"""Security regression tests for provider connections."""

import pytest

from app.core.config import settings
from app.security.credentials import (
    CredentialVaultError,
    decrypt_credentials,
    encrypt_credentials,
)
from app.security.oauth_state import OAuthStateError, create_oauth_state, decode_oauth_state


def test_credentials_round_trip_without_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "connections_encryption_key", "vault-secret-" * 4)
    encrypted = encrypt_credentials({"access_token": "github-secret", "refresh": "abc"})
    assert "github-secret" not in encrypted
    assert decrypt_credentials(encrypted) == {
        "access_token": "github-secret",
        "refresh": "abc",
    }


def test_wrong_vault_key_cannot_decrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "connections_encryption_key", "first-secret-" * 4)
    encrypted = encrypt_credentials({"bot_token": "xoxb-secret"})
    monkeypatch.setattr(settings, "connections_encryption_key", "second-secret-" * 4)
    with pytest.raises(CredentialVaultError):
        decrypt_credentials(encrypted)


def test_oauth_state_binds_user_organization_and_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "oauth_state_secret", "oauth-secret-" * 4)
    token = create_oauth_state("github", 42, "org-ark")
    payload = decode_oauth_state(token, "github")
    assert payload["user_id"] == 42
    assert payload["organization_id"] == "org-ark"
    with pytest.raises(OAuthStateError):
        decode_oauth_state(token, "slack")
