"""Signed provider state must protect installation context between redirects."""

import pytest

from app.core.config import settings
from app.security.oauth_state import OAuthStateError, create_oauth_state, decode_oauth_state


def test_installation_id_round_trips_inside_signed_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "oauth_state_secret", "state-secret-" * 4)
    token = create_oauth_state(
        "github",
        7,
        "organization-9",
        extra={"installation_id": 12345},
    )
    payload = decode_oauth_state(token, "github")
    assert payload["user_id"] == 7
    assert payload["organization_id"] == "organization-9"
    assert payload["installation_id"] == 12345


def test_extra_context_cannot_replace_reserved_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "oauth_state_secret", "state-secret-" * 4)
    with pytest.raises(OAuthStateError, match="reserved"):
        create_oauth_state(
            "github",
            7,
            "organization-9",
            extra={"user_id": 999},
        )
