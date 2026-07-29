"""Encrypted credential vault for user-owned provider connections."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialVaultError(RuntimeError):
    """Raised when provider credentials cannot be safely encrypted or decrypted."""


def _fernet() -> Fernet:
    secret = settings.connections_encryption_key.strip()
    if len(secret) < 32:
        raise CredentialVaultError(
            "CONNECTIONS_ENCRYPTION_KEY must contain at least 32 characters."
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    payload = json.dumps(
        credentials,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _fernet().encrypt(payload).decode("ascii")


def decrypt_credentials(ciphertext: str) -> dict[str, Any]:
    try:
        raw = _fernet().decrypt(ciphertext.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialVaultError(
            "The provider connection could not be decrypted. Reconnect the account."
        ) from exc
    if not isinstance(payload, dict):
        raise CredentialVaultError("Invalid provider credential payload.")
    return payload
