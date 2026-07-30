"""ClickUp list/task source and destination adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.providers.common import ProviderRuntimeError, is_after


def _token(credentials: dict[str, Any]) -> str:
    token = str(credentials.get("access_token") or "").strip()
    if not token:
        raise ProviderRuntimeError("Reconecte o ClickUp antes de usar esta conexão.")
    return token


async def _request(
    credentials: dict[str, Any],
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{settings.clickup_base_url}{path}",
            headers={"Authorization": f"Bearer {_token(credentials)}"},
            params=params,
            json=json,
        )
    payload = response.json()
    if not response.is_success:
        if response.status_code in {401, 403}:
            raise ProviderRuntimeError(
                "O ClickUp revogou ou limitou esta conexão. Reconecte o workspace."
            )
        message = str(payload.get("err") or payload.get("error") or response.status_code)
        raise ProviderRuntimeError(f"O ClickUp recusou a operação: {message}.")
    return payload


async def list_resources(
    credentials: dict[str, Any], role: str
) -> list[dict[str, Any]]:
    del role
    workspaces = (await _request(credentials, "GET", "/team")).get("teams", [])
    resources: list[dict[str, Any]] = []
    for workspace in workspaces[:20]:
        workspace_id = str(workspace.get("id") or "")
        workspace_name = str(workspace.get("name") or "ClickUp")
        if not workspace_id:
            continue
        spaces = (
            await _request(
                credentials,
                "GET",
                f"/team/{workspace_id}/space",
                params={"archived": "false"},
            )
        ).get("spaces", [])
        for space in spaces[:100]:
            space_id = str(space.get("id") or "")
            space_name = str(space.get("name") or "Espaço")
            if not space_id:
                continue
            folderless = (
                await _request(
                    credentials,
                    "GET",
                    f"/space/{space_id}/list",
                    params={"archived": "false"},
                )
            ).get("lists", [])
            for item in folderless:
                resources.append(
                    _list_resource(item, workspace_id, workspace_name, space_name, "")
                )
            folders = (
                await _request(
                    credentials,
                    "GET",
                    f"/space/{space_id}/folder",
                    params={"archived": "false"},
                )
            ).get("folders", [])
            for folder in folders[:100]:
                folder_name = str(folder.get("name") or "Pasta")
                for item in folder.get("lists", []):
                    resources.append(
                        _list_resource(
                            item,
                            workspace_id,
                            workspace_name,
                            space_name,
                            folder_name,
                        )
                    )
    return resources[:1000]


def _list_resource(
    item: dict[str, Any],
    workspace_id: str,
    workspace_name: str,
    space_name: str,
    folder_name: str,
) -> dict[str, Any]:
    list_id = str(item.get("id") or "")
    name = str(item.get("name") or "Lista")
    path = " / ".join(part for part in (workspace_name, space_name, folder_name, name) if part)
    return {
        "id": list_id,
        "name": name,
        "label": path,
        "type": "list",
        "private": False,
        "available": bool(list_id),
        "metadata": {
            "workspaceId": workspace_id,
            "workspaceName": workspace_name,
            "spaceName": space_name,
            "folderName": folder_name,
        },
    }


async def collect(
    credentials: dict[str, Any],
    config: dict[str, Any],
    *,
    since: datetime | None,
    trial_limits: bool,
) -> dict[str, Any]:
    list_id = str(config.get("resourceId") or "").strip()
    label = str(config.get("resourceLabel") or list_id)
    if not list_id:
        raise ProviderRuntimeError("Escolha uma lista do ClickUp para a fonte.")
    params: dict[str, Any] = {
        "archived": "false",
        "include_closed": "true",
        "subtasks": "true",
        "page": 0,
    }
    if since is not None:
        reference = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
        params["date_updated_gt"] = int(reference.timestamp() * 1000)
    payload = await _request(
        credentials, "GET", f"/list/{list_id}/task", params=params
    )
    limit = 40 if trial_limits else 200
    events: list[dict[str, Any]] = []
    for item in payload.get("tasks", [])[:limit]:
        updated_ms = item.get("date_updated")
        occurred_at = ""
        try:
            occurred_at = datetime.fromtimestamp(
                int(updated_ms) / 1000, tz=timezone.utc
            ).isoformat()
        except (TypeError, ValueError, OSError):
            occurred_at = str(updated_ms or "")
        if not is_after(occurred_at, since):
            continue
        status = item.get("status") or {}
        assignees = item.get("assignees") or []
        events.append(
            {
                "type": "work_item",
                "source": "clickup",
                "container": label,
                "title": str(item.get("name") or "Tarefa"),
                "description": str(
                    item.get("text_content") or item.get("description") or ""
                ),
                "actor": ", ".join(
                    str(person.get("username") or person.get("email") or "")
                    for person in assignees
                ),
                "status": str(status.get("status") or ""),
                "occurred_at": occurred_at,
                "reference": str(item.get("id") or ""),
                "labels": [
                    str(tag.get("name") or "") for tag in item.get("tags", [])
                ],
            }
        )
    return {
        "source_provider": "clickup",
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
        raise ProviderRuntimeError("Escolha uma lista do ClickUp para o destino.")
    payload = await _request(
        credentials,
        "POST",
        f"/list/{list_id}/task",
        json={
            "name": title[:2000],
            "description": f"{content}\n\nArkLog-ID: {idempotency_key}"[:60000],
            "notify_all": False,
        },
    )
    return {
        "external_id": str(payload.get("id") or ""),
        "target_id": list_id,
        "provider": "clickup",
        "url": payload.get("url"),
    }
