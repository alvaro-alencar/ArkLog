"""Notion page and data-source adapter."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.providers.common import (
    ProviderRuntimeError,
    chunk_text,
    is_after,
)


def _token(credentials: dict[str, Any]) -> str:
    token = str(credentials.get("access_token") or "").strip()
    if not token:
        raise ProviderRuntimeError("Reconecte o Notion antes de usar esta conexão.")
    return token


def _headers(credentials: dict[str, Any]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token(credentials)}",
        "Notion-Version": settings.notion_api_version,
        "Content-Type": "application/json",
    }


async def _refresh(credentials: dict[str, Any], client: httpx.AsyncClient) -> bool:
    refresh_token = str(credentials.get("refresh_token") or "").strip()
    if not refresh_token or not settings.notion_oauth_configured:
        return False
    encoded = base64.b64encode(
        f"{settings.notion_client_id}:{settings.notion_client_secret}".encode("utf-8")
    ).decode("ascii")
    response = await client.post(
        f"{settings.notion_api_base_url}/oauth/token",
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Notion-Version": settings.notion_api_version,
        },
        json={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    payload = response.json()
    if not response.is_success or not payload.get("access_token"):
        return False
    credentials["access_token"] = payload["access_token"]
    credentials["refresh_token"] = payload.get("refresh_token") or refresh_token
    credentials["_dirty"] = True
    return True


async def _request(
    credentials: dict[str, Any],
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{settings.notion_api_base_url}{path}",
            headers=_headers(credentials),
            json=json,
        )
        if response.status_code == 401 and await _refresh(credentials, client):
            response = await client.request(
                method,
                f"{settings.notion_api_base_url}{path}",
                headers=_headers(credentials),
                json=json,
            )
    payload = response.json()
    if not response.is_success:
        code = str(payload.get("code") or response.status_code)
        message = str(payload.get("message") or "")
        if response.status_code in {401, 403}:
            raise ProviderRuntimeError(
                "O Notion não autorizou este conteúdo. Reconecte a conta e confirme as páginas compartilhadas."
            )
        raise ProviderRuntimeError(f"O Notion recusou a operação: {code}. {message}".strip())
    return payload


def _plain_text(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    return "".join(str(item.get("plain_text") or "") for item in items if isinstance(item, dict))


def _page_title(item: dict[str, Any]) -> str:
    if item.get("object") == "data_source":
        return _plain_text(item.get("title")) or "Base do Notion"
    for prop in (item.get("properties") or {}).values():
        if not isinstance(prop, dict):
            continue
        if prop.get("type") == "title":
            title = _plain_text(prop.get("title"))
            if title:
                return title
    return "Página do Notion"


def _property_summary(properties: dict[str, Any]) -> str:
    parts: list[str] = []
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        value = ""
        if prop_type in {"title", "rich_text"}:
            value = _plain_text(prop.get(prop_type))
        elif prop_type in {"select", "status"}:
            value = str((prop.get(prop_type) or {}).get("name") or "")
        elif prop_type == "multi_select":
            value = ", ".join(
                str(item.get("name") or "") for item in prop.get("multi_select", [])
            )
        elif prop_type == "checkbox":
            value = "sim" if prop.get("checkbox") else "não"
        elif prop_type == "number":
            value = str(prop.get("number") if prop.get("number") is not None else "")
        elif prop_type == "date":
            value = str((prop.get("date") or {}).get("start") or "")
        if value:
            parts.append(f"{name}: {value}")
    return " · ".join(parts)[:1200]


async def list_resources(
    credentials: dict[str, Any], role: str
) -> list[dict[str, Any]]:
    del role
    resources: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(5):
        body: dict[str, Any] = {
            "page_size": 100,
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        }
        if cursor:
            body["start_cursor"] = cursor
        payload = await _request(credentials, "POST", "/search", json=body)
        for item in payload.get("results", []):
            object_type = str(item.get("object") or "")
            if object_type not in {"page", "data_source"}:
                continue
            resources.append(
                {
                    "id": str(item.get("id") or ""),
                    "name": _page_title(item),
                    "label": _page_title(item),
                    "type": object_type,
                    "private": False,
                    "available": True,
                    "metadata": {
                        "url": item.get("url"),
                        "lastEditedTime": item.get("last_edited_time"),
                    },
                }
            )
        cursor = payload.get("next_cursor")
        if not payload.get("has_more") or not cursor:
            break
    return resources


async def collect(
    credentials: dict[str, Any],
    config: dict[str, Any],
    *,
    since: datetime | None,
    trial_limits: bool,
) -> dict[str, Any]:
    resource_id = str(config.get("resourceId") or "").strip()
    resource_type = str(config.get("resourceType") or "page").strip()
    label = str(config.get("resourceLabel") or "Notion").strip()
    if not resource_id:
        raise ProviderRuntimeError("Escolha uma página ou base do Notion para a fonte.")
    limit = 40 if trial_limits else 200
    events: list[dict[str, Any]] = []

    if resource_type == "data_source":
        cursor: str | None = None
        while len(events) < limit:
            body: dict[str, Any] = {"page_size": min(100, limit - len(events))}
            if cursor:
                body["start_cursor"] = cursor
            payload = await _request(
                credentials,
                "POST",
                f"/data_sources/{resource_id}/query",
                json=body,
            )
            for item in payload.get("results", []):
                if not is_after(item.get("last_edited_time"), since):
                    continue
                events.append(
                    {
                        "type": "work_item",
                        "source": "notion",
                        "container": label,
                        "title": _page_title(item),
                        "description": _property_summary(item.get("properties") or {}),
                        "actor": str((item.get("last_edited_by") or {}).get("id") or ""),
                        "status": "updated",
                        "occurred_at": item.get("last_edited_time", ""),
                        "reference": str(item.get("id") or ""),
                    }
                )
            cursor = payload.get("next_cursor")
            if not payload.get("has_more") or not cursor:
                break
    else:
        payload = await _request(
            credentials,
            "GET",
            f"/blocks/{resource_id}/children?page_size={min(limit, 100)}",
        )
        content_parts: list[str] = []
        for block in payload.get("results", []):
            block_type = str(block.get("type") or "")
            block_value = block.get(block_type) or {}
            text = _plain_text(block_value.get("rich_text"))
            if text:
                content_parts.append(text)
        events.append(
            {
                "type": "document",
                "source": "notion",
                "container": label,
                "title": label,
                "description": "\n".join(content_parts)[:8000],
                "actor": "",
                "status": "current",
                "occurred_at": "",
                "reference": resource_id,
            }
        )

    return {
        "source_provider": "notion",
        "source_label": label,
        "normalized_events": events[:limit],
        "raw_item_count": len(events[:limit]),
    }


async def publish(
    credentials: dict[str, Any],
    config: dict[str, Any],
    *,
    title: str,
    content: str,
    idempotency_key: str,
) -> dict[str, Any]:
    del idempotency_key
    resource_id = str(config.get("resourceId") or "").strip()
    resource_type = str(config.get("resourceType") or "page").strip()
    if not resource_id:
        raise ProviderRuntimeError("Escolha uma página ou base do Notion para o destino.")

    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        }
        for chunk in chunk_text(content, 1800)[:90]
    ]
    if resource_type == "data_source":
        data_source = await _request(
            credentials, "GET", f"/data_sources/{resource_id}"
        )
        title_property = next(
            (
                name
                for name, prop in (data_source.get("properties") or {}).items()
                if isinstance(prop, dict) and prop.get("type") == "title"
            ),
            "Name",
        )
        body = {
            "parent": {"type": "data_source_id", "data_source_id": resource_id},
            "properties": {
                title_property: {
                    "type": "title",
                    "title": [{"type": "text", "text": {"content": title[:1900]}}],
                }
            },
            "children": children,
        }
    else:
        body = {
            "parent": {"type": "page_id", "page_id": resource_id},
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"type": "text", "text": {"content": title[:1900]}}],
                }
            },
            "children": children,
        }
    payload = await _request(credentials, "POST", "/pages", json=body)
    return {
        "external_id": str(payload.get("id") or ""),
        "target_id": resource_id,
        "provider": "notion",
        "url": payload.get("url"),
    }
