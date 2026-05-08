"""
ArkLog - GitHub Webhook Receiver

Receives and validates GitHub webhook events, then dispatches them
to the internal event bus. Phase 2 adds full commit parsing.

Security: every request is validated against the HMAC-SHA256 signature
that GitHub attaches to the X-Hub-Signature-256 header.
"""

import structlog
from fastapi import APIRouter, Depends, Request, status

from app.core.events import event_bus
from app.integrations.github.webhook_validator import validate_github_signature

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def receive_github_webhook(
    request: Request,
    _: None = Depends(validate_github_signature),
) -> dict:
    """
    Entry point for all GitHub webhook events.

    Validates HMAC-SHA256 signature, then routes by event type.
    Returns 202 immediately — processing is async via the event bus.
    """
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
    payload = await request.json()

    logger.info(
        "webhook_received",
        event_type=event_type,
        delivery_id=delivery_id,
        repo=payload.get("repository", {}).get("full_name", "unknown"),
    )

    match event_type:
        case "push":
            await event_bus.publish("github.push", payload)
        case "pull_request":
            await event_bus.publish("github.pull_request", payload)
        case "issues":
            await event_bus.publish("github.issues", payload)
        case "workflow_run":
            await event_bus.publish("github.workflow_run", payload)
        case "release":
            await event_bus.publish("github.release", payload)
        case "ping":
            logger.info("webhook_ping", zen=payload.get("zen", ""))
        case _:
            logger.debug("webhook_unhandled_event", event_type=event_type)

    return {"status": "accepted", "delivery_id": delivery_id}
