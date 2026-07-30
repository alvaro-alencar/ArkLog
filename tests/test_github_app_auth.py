"""Security regressions for least-privilege GitHub App connections."""

import json

import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import Response

from app.core.config import settings
from app.integrations.github.app_auth import (
    GitHubAppError,
    create_app_jwt,
    create_installation_token,
    resolve_user_installation,
)


@pytest.fixture
def github_app(monkeypatch: pytest.MonkeyPatch) -> bytes:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    monkeypatch.setattr(settings, "github_app_id", "12345")
    monkeypatch.setattr(settings, "github_app_slug", "arklog-test")
    monkeypatch.setattr(settings, "github_app_private_key", private_pem)
    monkeypatch.setattr(settings, "github_client_id", "Iv1.test-client")
    monkeypatch.setattr(settings, "github_client_secret", "test-secret")
    monkeypatch.setattr(
        settings,
        "github_setup_uri",
        "https://www.arksystem.net/api/arklog/v1/connections/github/setup",
    )
    monkeypatch.setattr(
        settings,
        "github_redirect_uri",
        "https://www.arksystem.net/api/arklog/v1/connections/github/callback",
    )
    return public_pem


def test_app_jwt_is_short_lived_and_rs256(github_app: bytes) -> None:
    token = create_app_jwt(now=1_000_000)
    header = jwt.get_unverified_header(token)
    payload = jwt.decode(
        token,
        github_app,
        algorithms=["RS256"],
        options={"verify_exp": False},
    )
    assert header["alg"] == "RS256"
    assert payload["iss"] == "Iv1.test-client"
    assert payload["iat"] == 999_940
    assert payload["exp"] == 1_000_540
    assert payload["exp"] - payload["iat"] <= 600


@pytest.mark.asyncio
@respx.mock
async def test_installation_token_is_restricted_to_one_repository(github_app: bytes) -> None:
    route = respx.post(
        "https://api.github.com/app/installations/77/access_tokens"
    ).mock(
        return_value=Response(
            201,
            json={"token": "ghs_short_lived", "expires_at": "2026-07-30T13:00:00Z"},
        )
    )

    token = await create_installation_token(77, repository_id=4242)

    assert token == "ghs_short_lived"
    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body == {"repository_ids": [4242]}
    assert route.calls[0].request.headers["authorization"].startswith("Bearer ")


@pytest.mark.asyncio
@respx.mock
async def test_user_must_own_the_selected_installation(github_app: bytes) -> None:
    route = respx.get("https://api.github.com/user/installations").mock(
        return_value=Response(
            200,
            json={
                "total_count": 1,
                "installations": [
                    {
                        "id": 77,
                        "app_id": 12345,
                        "account": {"id": 9, "login": "authorized-user"},
                    }
                ],
            },
        )
    )

    installation = await resolve_user_installation("temporary-user-token", 77)
    assert installation["id"] == 77
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_foreign_installation_is_rejected(github_app: bytes) -> None:
    respx.get("https://api.github.com/user/installations").mock(
        return_value=Response(
            200,
            json={
                "total_count": 1,
                "installations": [
                    {
                        "id": 88,
                        "app_id": 12345,
                        "account": {"id": 10, "login": "another-user"},
                    }
                ],
            },
        )
    )

    with pytest.raises(GitHubAppError, match="does not belong"):
        await resolve_user_installation("temporary-user-token", 77)
