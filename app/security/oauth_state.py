"""Short-lived signed state for provider OAuth callbacks."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings


class OAuthStateError(RuntimeError):
    """Raised when an OAuth state token is missing, expired or tampered with."""


def create_oauth_state(
    provider: str,
    user_id: int,
    organization_id: str,
) -> str:
    secret = settings.oauth_state_secret.strip()
    if len(secret) < 32:
        raise OAuthStateError("OAUTH_STATE_SECRET must contain at least 32 characters.")
    now = datetime.now(UTC)
    payload = {
        "provider": provider,
        "user_id": user_id,
        "organization_id": organization_id,
        "nonce": secrets.token_urlsafe(18),
        "iat": now,
        "exp": now + timedelta(seconds=settings.oauth_state_ttl_seconds),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_oauth_state(token: str, expected_provider: str) -> dict[str, Any]:
    secret = settings.oauth_state_secret.strip()
    if len(secret) < 32:
        raise OAuthStateError("OAuth state validation is not configured.")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise OAuthStateError("OAuth state is invalid or expired.") from exc
    if payload.get("provider") != expected_provider:
        raise OAuthStateError("OAuth provider does not match the signed state.")
    if not payload.get("user_id") or not payload.get("organization_id"):
        raise OAuthStateError("OAuth state is incomplete.")
    return payload
