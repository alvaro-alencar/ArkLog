"""Trello board/list source and destination adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.providers.common import ProviderRuntimeError, is_after


def _token(credentials: dict[str, Any]) -> str:
    token = str(credentials.get("user_token") or "").strip()
    if not token:
        raise ProviderRuntimeError("Reconecte o Trello antes de usar esta conexão.")
    if not settings.trello_api_key:
        raise ProviderRuntimeError("O aplicativo Trello do ArkLog ainda não foi configurado.")
    return token


async def _request(
    credentials: dict[str, Any],
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:
    query = {"key": settings.trello_api_key, "token": _token(credentials)}
    query.update(params or {})
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{settings.trello_api_base_url}{path}",
            params=query,
            headers={"Accept": "application/json"},
        )
    payload = response.json()
    if not response.is_success:
        if response.status_code in {401, 403}:
            raise ProviderRuntimeError(
                "O Trello revogou esta autorização. Reconecte sua conta."
            )
        message = payload.get("message") if isinstance(payload, dict) else response.text
        raise ProviderRuntimeError(f"O Trello recusou a operação: {message}.")
    return payload


async def list_resources(
    credentials: dict[str, Any], role: str
) -> list[dict[str, Any]]:
    boards = await _request(
        credentials,
        "GET",
        "/members/me/boards",
        params={"filter": "open", "fields": "name,url,closed"},
    )
    if role == "source":
        return [
            {
                "id": str(board.get("id") or ""),
                "name": board.get("name"),
                "label": board.get("name"),
                "type": "board",
                "private": False,
                "available": not bool(board.get("closed")),
                "metadata": {"url": board.get("url")},
            }
            for board in boards
            if board.get("id")
        ]

    resources: list[dict[str, Any]] = []
    for board in boards[:100]:
        board_id = str(board.get("id") or "")
        if not board_id:
            continue
        lists = await _request(
            credentials,
            "GET",
            f"/boards/{board_id}/lists",
            params={"filter": "open", "fields": "name,closed,idBoard"},
        )
        for item in lists:
            resources.append(
                {
                    "id": str(item.get("id") or ""),
                    "name": item.get("name"),
                    "label": f"{board.get('name')} / {item.get('name')}",
                    "type": "list",
                    "private": False,
                    "available": not bool(item.get("closed")),
                    "metadata": {
                        "boardId": board_id,
                        "boardName": board.get("name"),
                        "boardUrl": board.get("url"),
                    },
                }
            )
    return resources[:1000]


async def collect(
    credentials: dict[str, Any],
    config: dict[str, Any],
    *,
    since: datetime | None,
    trial_limits: bool,
) -> dict[str, Any]:
    board_id = str(config.get("resourceId") or "").strip()
    label = str(config.get("resourceLabel") or board_id)
    if not board_id:
        raise ProviderRuntimeError("Escolha um quadro do Trello para a fonte.")
    cards = await _request(
        credentials,
        "GET",
        f"/boards/{board_id}/cards",
        params={
            "filter": "all",
            "fields": "name,desc,closed,dateLastActivity,url,idList,labels",
        },
    )
    limit = 40 if trial_limits else 300
    events: list[dict[str, Any]] = []
    for item in cards:
        if not is_after(item.get("dateLastActivity"), since):
            continue
        events.append(
            {
                "type": "work_item",
                "source": "trello",
                "container": label,
                "title": str(item.get("name") or "Cartão"),
                "description": str(item.get("desc") or ""),
                "actor": "",
                "status": "archived" if item.get("closed") else "open",
                "occurred_at": item.get("dateLastActivity", ""),
                "reference": str(item.get("url") or item.get("id") or ""),
                "labels": [
                    str(tag.get("name") or tag.get("color") or "")
                    for tag in item.get("labels", [])
                ],
            }
        )
        if len(events) >= limit:
            break
    return {
        "source_provider": "trello",
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
    list_id = str(config.get("resourceId") or "").strip()
    if not list_id:
        raise ProviderRuntimeError("Escolha uma lista do Trello para o destino.")
    payload = await _request(
        credentials,
        "POST",
        "/cards",
        params={
            "idList": list_id,
            "name": title[:16384],
            "desc": f"{content}\n\nArkLog-ID: {idempotency_key}"[:16384],
            "pos": "top",
        },
    )
    return {
        "external_id": str(payload.get("id") or ""),
        "target_id": list_id,
        "provider": "trello",
        "url": payload.get("url"),
    }
