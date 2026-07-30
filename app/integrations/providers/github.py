"""GitHub source adapter using least-privilege installation tokens."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.integrations.github.app_auth import (
    GitHubAppError,
    create_installation_token,
    list_installation_repositories,
)
from app.integrations.providers.common import ProviderRuntimeError


def _installation_id(credentials: dict[str, Any]) -> int:
    try:
        value = int(credentials.get("installation_id") or 0)
    except (TypeError, ValueError) as exc:
        raise ProviderRuntimeError(
            "Reinstale o GitHub App antes de usar esta conexão."
        ) from exc
    if value <= 0:
        raise ProviderRuntimeError("Reinstale o GitHub App antes de usar esta conexão.")
    return value


async def list_resources(
    credentials: dict[str, Any], role: str
) -> list[dict[str, Any]]:
    if role != "source":
        return []
    try:
        items = await list_installation_repositories(_installation_id(credentials))
    except GitHubAppError as exc:
        raise ProviderRuntimeError(str(exc)) from exc
    return [
        {
            "id": str(repo.get("full_name") or ""),
            "name": repo.get("full_name"),
            "label": repo.get("full_name"),
            "type": "repository",
            "private": bool(repo.get("private")),
            "available": True,
            "metadata": {
                "repositoryId": repo.get("id"),
                "url": repo.get("html_url"),
            },
        }
        for repo in items
        if repo.get("id") and repo.get("full_name")
    ]


async def collect(
    credentials: dict[str, Any],
    config: dict[str, Any],
    *,
    since: datetime | None,
    trial_limits: bool,
) -> dict[str, Any]:
    repo_full_name = str(
        config.get("resourceId") or config.get("repository") or ""
    ).strip()
    if repo_full_name.count("/") != 1:
        raise ProviderRuntimeError("Escolha um repositório GitHub para a fonte.")

    installation_id = _installation_id(credentials)
    try:
        selected_repositories = await list_installation_repositories(installation_id)
        selected = next(
            (
                item
                for item in selected_repositories
                if str(item.get("full_name") or "").casefold()
                == repo_full_name.casefold()
            ),
            None,
        )
        if selected is None:
            raise ProviderRuntimeError(
                "Este repositório não está mais selecionado na instalação do GitHub App."
            )
        repository_id = int(selected.get("id") or 0)
        if repository_id <= 0:
            raise ProviderRuntimeError("O GitHub retornou um repositório inválido.")
        token = await create_installation_token(
            installation_id,
            repository_id=repository_id,
        )
    except GitHubAppError as exc:
        raise ProviderRuntimeError(str(exc)) from exc

    owner, repo = repo_full_name.split("/", 1)
    from app.integrations.github.api_client import fetch_github_activity

    activity = await fetch_github_activity(
        owner,
        repo,
        since=since,
        token=token,
        use_global_token=False,
        trial_limits=trial_limits,
    )
    events = _normalize(repo_full_name, activity)
    return {
        **activity,
        "source_provider": "github",
        "source_label": repo_full_name,
        "normalized_events": events,
        "raw_item_count": len(events),
    }


def _normalize(source_label: str, activity: dict[str, Any]) -> list[dict[str, Any]]:
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
