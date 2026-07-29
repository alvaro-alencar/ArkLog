"""Runtime adapters for provider-agnostic ArkLog flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings
from app.models.tables import IntegrationConnectionRecord
from app.security.credentials import decrypt_credentials


class IntegrationRuntimeError(RuntimeError):
    """Safe provider failure that can be shown without leaking credentials."""


async def list_connection_resources(
    connection: IntegrationConnectionRecord,
) -> list[dict[str, Any]]:
    credentials = decrypt_credentials(connection.encrypted_credentials)
    if connection.provider == "github":
        return await _github_repositories(credentials)
    if connection.provider == "slack":
        return await _slack_channels(credentials)
    raise IntegrationRuntimeError(f"Provider {connection.provider} is not supported yet.")


async def collect_source(
    connection: IntegrationConnectionRecord,
    config: dict[str, Any],
    *,
    since: datetime | None,
    trial_limits: bool,
) -> dict[str, Any]:
    """Collect a provider payload and attach a provider-neutral event envelope."""
    if connection.provider != "github":
        raise IntegrationRuntimeError(
            f"Provider {connection.provider} is not available as a source yet."
        )
    repo_full_name = str(config.get("repository") or "").strip()
    if "/" not in repo_full_name:
        raise IntegrationRuntimeError("Choose a GitHub repository for the source.")
    owner, repo = repo_full_name.split("/", 1)
    credentials = decrypt_credentials(connection.encrypted_credentials)
    token = str(credentials.get("access_token") or "")
    if not token:
        raise IntegrationRuntimeError("Reconnect GitHub before running this flow.")

    from app.integrations.github.api_client import fetch_github_activity

    activity = await fetch_github_activity(
        owner,
        repo,
        since=since,
        token=token,
        use_global_token=False,
        trial_limits=trial_limits,
    )
    return {
        **activity,
        "source_provider": "github",
        "source_label": repo_full_name,
        "normalized_events": _normalize_github_activity(repo_full_name, activity),
    }


async def publish_destination(
    connection: IntegrationConnectionRecord,
    config: dict[str, Any],
    content: str,
    *,
    idempotency_key: str,
) -> dict[str, Any]:
    """Publish with a stable provider-side message ID when the destination supports it."""
    if connection.provider != "slack":
        raise IntegrationRuntimeError(
            f"Provider {connection.provider} is not available as a destination yet."
        )
    channel_id = str(config.get("channel") or "").strip()
    if not channel_id:
        raise IntegrationRuntimeError("Choose a Slack channel for the destination.")
    credentials = decrypt_credentials(connection.encrypted_credentials)
    token = str(credentials.get("bot_token") or "")
    if not token:
        raise IntegrationRuntimeError("Reconnect Slack before running this flow.")

    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            f"{settings.slack_api_base_url}/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "channel": channel_id,
                "text": content[:39000],
                "client_msg_id": idempotency_key[:36],
                "unfurl_links": False,
                "unfurl_media": False,
            },
        )
    payload = response.json()
    if not response.is_success or not payload.get("ok"):
        error = str(payload.get("error") or response.status_code)
        raise IntegrationRuntimeError(f"Slack rejected the publication: {error}.")
    return {
        "external_id": str(payload.get("ts") or ""),
        "target_id": channel_id,
        "provider": "slack",
    }


def _normalize_github_activity(
    source_label: str,
    activity: dict[str, Any],
) -> list[dict[str, Any]]:
    """Turn GitHub-specific objects into the stable contract consumed by the LLM."""
    events: list[dict[str, Any]] = []
    for item in activity.get("commits", []):
        events.append(
            {
                "type": "change",
                "source": "github",
                "container": source_label,
                "title": item.get("subject", ""),
                "description": item.get("body", ""),
                "actor": item.get("author", ""),
                "status": "completed",
                "occurred_at": item.get("committed_at", ""),
                "reference": item.get("short_sha", ""),
            }
        )
    for item in activity.get("pull_requests", []):
        events.append(
            {
                "type": "review",
                "source": "github",
                "container": source_label,
                "title": item.get("title", ""),
                "description": item.get("body", ""),
                "actor": item.get("author", ""),
                "status": item.get("state", ""),
                "occurred_at": item.get("merged_at")
                or item.get("closed_at")
                or item.get("created_at", ""),
                "reference": f"PR #{item.get('number')}",
                "labels": item.get("labels", []),
            }
        )
    for item in activity.get("issues", []):
        events.append(
            {
                "type": "work_item",
                "source": "github",
                "container": source_label,
                "title": item.get("title", ""),
                "description": item.get("body", ""),
                "actor": item.get("author", ""),
                "status": item.get("state", ""),
                "occurred_at": item.get("closed_at") or item.get("created_at", ""),
                "reference": f"Issue #{item.get('number')}",
                "labels": item.get("labels", []),
            }
        )
    for item in activity.get("workflow_runs", []):
        events.append(
            {
                "type": "automation",
                "source": "github",
                "container": source_label,
                "title": item.get("name", ""),
                "description": item.get("commit_subject", ""),
                "actor": "",
                "status": item.get("conclusion") or item.get("status", ""),
                "occurred_at": item.get("created_at", ""),
                "reference": item.get("branch", ""),
            }
        )
    for item in activity.get("releases", []):
        events.append(
            {
                "type": "release",
                "source": "github",
                "container": source_label,
                "title": item.get("name", ""),
                "description": item.get("body", ""),
                "actor": item.get("author", ""),
                "status": "prerelease" if item.get("prerelease") else "published",
                "occurred_at": item.get("published_at", ""),
                "reference": item.get("tag", ""),
            }
        )
    return events


async def _github_repositories(credentials: dict[str, Any]) -> list[dict[str, Any]]:
    token = str(credentials.get("access_token") or "")
    if not token:
        raise IntegrationRuntimeError("GitHub connection has no active token.")
    resources: list[dict[str, Any]] = []
    page = 1
    async with httpx.AsyncClient(timeout=25.0) as client:
        while page <= 5:
            response = await client.get(
                f"{settings.github_api_base_url}/user/repos",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "ArkLog/0.3",
                },
                params={
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            if response.status_code in {401, 403}:
                raise IntegrationRuntimeError("Reconnect GitHub to refresh access.")
            response.raise_for_status()
            items = response.json()
            for repo in items:
                resources.append(
                    {
                        "id": str(repo.get("id")),
                        "name": repo.get("full_name"),
                        "label": repo.get("full_name"),
                        "private": bool(repo.get("private")),
                        "url": repo.get("html_url"),
                    }
                )
            if len(items) < 100:
                break
            page += 1
    return resources


async def _slack_channels(credentials: dict[str, Any]) -> list[dict[str, Any]]:
    token = str(credentials.get("bot_token") or "")
    if not token:
        raise IntegrationRuntimeError("Slack connection has no active bot token.")
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
                raise IntegrationRuntimeError(f"Slack channel listing failed: {error}.")
            for channel in payload.get("channels", []):
                resources.append(
                    {
                        "id": str(channel.get("id")),
                        "name": channel.get("name"),
                        "label": f"#{channel.get('name')}",
                        "private": bool(channel.get("is_private")),
                    }
                )
            cursor = str(payload.get("response_metadata", {}).get("next_cursor") or "")
            if not cursor:
                break
    return resources
