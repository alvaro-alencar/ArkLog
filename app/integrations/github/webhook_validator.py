"""
ArkLog - GitHub Webhook Signature Validator

Validates the HMAC-SHA256 signature GitHub attaches to every webhook delivery.
Prevents malicious actors from sending forged events to the ArkLog endpoint.

Ref: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
"""

import hashlib
import hmac

import structlog
from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = structlog.get_logger(__name__)


async def validate_github_signature(request: Request) -> None:
    """
    FastAPI dependency that validates X-Hub-Signature-256.

    Raises HTTP 401 if the signature is missing or invalid.
    Skipped entirely when GITHUB_WEBHOOK_SECRET is empty (local dev).
    """
    if not settings.github_webhook_secret:
        logger.warning("webhook_secret_not_set", note="Signature validation disabled")
        return

    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    body = await request.body()

    expected = "sha256=" + hmac.HMAC(
        settings.github_webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        logger.warning("webhook_invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
