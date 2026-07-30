"""Slack channel source and destination adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.providers.common import ProviderRuntimeError, is_after
from app.integrations.slack_errors import publication_error_message


def _token(credentials: dict[str, Any]) -> str:
    token = str(credentials.get("bot_token") or "").strip()
    if not token:
        raise ProviderRuntimeError("Reconecte o Slack antes de usar esta conexão.")
    return token


def _scope_set(credentials: dict[str, Any]) -> set[str]:
    values = credentials.get("_scopes") or credentials.get("scopes") or []
    if isinstance(values, str):
        values = values.split(",")
    return {str(item).strip() for item in values if str(item).strip()}


async def list_resources(
    credentials: dict[str, Any], role: str
) -> list[dict[str, Any]]:
    token = _token(credentials)
    scopes = _scope_set(credentials)
    resources: list[dict[str, Any]] = []
    cursor = ""
    async with httpx.AsyncClient(timeout=25.0) as client:
        for _ in range(5):
            response = await client.get(
                f"{settings.slack_api_base_url}/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "limit": 200,
                    "types": "public_channel,private_channel",
                    "exclude_archived": "true",
                    "cursor": cursor,
                },
            )
            payload = response.json()
            if not response.is_success or not payload.get("ok"):
                error = str(payload.get("error") or response.status_code)
                raise ProviderRuntimeError(f"O Slack não listou os canais: {error}.")
            for channel in payload.get("channels", []):
                private = bool(channel.get("is_private"))
                member = bool(channel.get("is_member"))
                history_scope = "groups:history" if private else "channels:history"
                if role == "source":
                    available = member and history_scope in scopes
                    if not member:
                        reason = "Convide @ArkLog para este canal antes de usá-lo como fonte."
                    elif history_scope not in scopes:
                        reason = "Reconecte o Slack para liberar leitura de mensagens."
                    else:
                        reason = ""
                else:
                    available = member
                    reason = (
                        "Convide @ArkLog para este canal antes de publicar relatórios."
                        if not member
                        else ""
                    )
                resources.append(
                    {
                        "id": str(channel.get("id") or ""),
                        "name": channel.get("name"),
                        "label": f"#{channel.get('name')}",
                        "type": "channel",
                        "private": private,
                        "available": available,
                        "availabilityReason": reason,
                        "metadata": {
                            "isMember": member,
                            "requiredScope": history_scope if role == "source" else "chat:write",
                        },
                    }
                )
            cursor = str(payload.get("response_metadata", {}).get("next_cursor") or "")
            if not cursor:
                break
    return resources


async def collect(
    credentials: dict[str, Any],
    config: dict[str, Any],
    *,
    since: datetime | None,
    trial_limits: bool,
) -> dict[str, Any]:
    del trial_limits
    channel_id = str(config.get("resourceId") or config.get("channel") or "").strip()
    label = str(config.get("resourceLabel") or config.get("channelLabel") or channel_id)
    if not channel_id:
        raise ProviderRuntimeError("Escolha um canal do Slack para a fonte.")
    token = _token(credentials)
    oldest = "0"
    if since is not None:
        reference = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
        oldest = str(reference.timestamp())

    messages: list[dict[str, Any]] = []
    cursor = ""
    async with httpx.AsyncClient(timeout=25.0) as client:
        for _ in range(5):
            response = await client.get(
                f"{settings.slack_api_base_url}/conversations.history",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": channel_id, "limit": 200, "oldest": oldest, "cursor": cursor},
            )
            payload = response.json()
            if not response.is_success or not payload.get("ok"):
                error = str(payload.get("error") or response.status_code)
                if error == "not_in_channel":
                    raise ProviderRuntimeError(
                        "O bot ArkLog precisa participar do canal para ler as mensagens. "
                        "No Slack, abra o canal e use /invite @ArkLog."
                    )
                if error == "missing_scope":
                    raise ProviderRuntimeError(
                        "Reconecte o Slack para autorizar a leitura das mensagens do canal."
                    )
                raise ProviderRuntimeError(f"O Slack recusou a leitura: {error}.")
            messages.extend(payload.get("messages", []))
            cursor = str(payload.get("response_metadata", {}).get("next_cursor") or "")
            if not cursor:
                break

    events = []
    for item in reversed(messages):
        timestamp = item.get("ts")
        occurred_at = ""
        try:
            occurred_at = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            occurred_at = str(timestamp or "")
        if not is_after(occurred_at, since):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        events.append(
            {
                "type": "message",
                "source": "slack",
                "container": label,
                "title": text[:120],
                "description": text,
                "actor": str(item.get("user") or item.get("bot_id") or ""),
                "status": "published",
                "occurred_at": occurred_at,
                "reference": str(timestamp or ""),
            }
        )
    return {
        "source_provider": "slack",
        "source_label": label,
        "normalized_events": events,
        "raw_item_count": len(events),
    }


async def publish(
    credentials: dict[str, Any],
    config: dict[str, Any],
    *,
    title: str,
    content: str,
    idempotency_key: str,
) -> dict[str, Any]:
    channel_id = str(config.get("resourceId") or config.get("channel") or "").strip()
    if not channel_id:
        raise ProviderRuntimeError("Escolha um canal do Slack para o destino.")
    token = _token(credentials)
    text = f"*{title}*\n\n{content}".strip()[:39000]
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            f"{settings.slack_api_base_url}/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "channel": channel_id,
                "text": text,
                "client_msg_id": idempotency_key[:36],
                "unfurl_links": False,
                "unfurl_media": False,
            },
        )
    payload = response.json()
    if not response.is_success or not payload.get("ok"):
        error = str(payload.get("error") or response.status_code)
        raise ProviderRuntimeError(publication_error_message(error))
    return {
        "external_id": str(payload.get("ts") or ""),
        "target_id": channel_id,
        "provider": "slack",
    }
