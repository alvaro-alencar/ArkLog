"""GitHub REST client with per-request credentials and bounded trial reads."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx
import structlog

from app.core.config import settings
from app.domain.entities.commit import Commit
from app.utils.datetime_utils import parse_github_timestamp

logger = structlog.get_logger(__name__)
_GITHUB_API = "https://api.github.com"
_PER_PAGE = 100


def _headers(token: str | None = None, use_global_token: bool = True) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ArkLog/0.2",
    }
    effective_token = token or (settings.github_token if use_global_token else "")
    if effective_token:
        headers["Authorization"] = f"Bearer {effective_token}"
    return headers


def _fmt_since(since: datetime) -> str:
    return since.strftime("%Y-%m-%dT%H:%M:%SZ")


async def fetch_repository_metadata(
    owner: str,
    repo: str,
    *,
    token: str | None = None,
    use_global_token: bool = True,
) -> dict[str, Any]:
    async with httpx.AsyncClient(
        headers=_headers(token, use_global_token), timeout=20.0
    ) as client:
        response = await client.get(f"{_GITHUB_API}/repos/{owner}/{repo}")
    if response.status_code == 404:
        raise RuntimeError(f"Repository {owner}/{repo} not found or not accessible.")
    response.raise_for_status()
    return response.json()


async def fetch_commits_since(
    owner: str,
    repo: str,
    since: datetime | None = None,
    *,
    token: str | None = None,
    use_global_token: bool = True,
    max_pages: int | None = None,
) -> list[Commit]:
    commits: list[Commit] = []
    page = 1
    params: dict[str, Any] = {"per_page": _PER_PAGE}
    if since:
        params["since"] = _fmt_since(since)

    async with httpx.AsyncClient(
        headers=_headers(token, use_global_token), timeout=30.0
    ) as client:
        while True:
            response = await client.get(
                f"{_GITHUB_API}/repos/{owner}/{repo}/commits",
                params={**params, "page": page},
            )
            if response.status_code in (401, 403):
                raise RuntimeError(f"GitHub access denied for {owner}/{repo}.")
            if response.status_code == 404:
                raise RuntimeError(f"Repository {owner}/{repo} not found.")
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for item in items:
                git = item.get("commit", {})
                author = git.get("author") or git.get("committer") or {}
                commits.append(
                    Commit(
                        sha=item["sha"],
                        message=git.get("message", ""),
                        author_name=author.get("name", "unknown"),
                        author_email=author.get("email", ""),
                        timestamp=parse_github_timestamp(author.get("date", "")),
                        url=item.get("html_url", ""),
                        repo_full_name=f"{owner}/{repo}",
                        branch="",
                        files=(),
                    )
                )
            if len(items) < _PER_PAGE or (max_pages and page >= max_pages):
                break
            page += 1
    return commits


async def fetch_all_commits(
    owner: str,
    repo: str,
    *,
    token: str | None = None,
    use_global_token: bool = True,
) -> list[Commit]:
    return await fetch_commits_since(
        owner, repo, token=token, use_global_token=use_global_token
    )


async def _fetch_issues_and_prs(
    owner: str,
    repo: str,
    since: datetime | None,
    *,
    token: str | None,
    use_global_token: bool,
    max_pages: int | None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "state": "all",
        "per_page": _PER_PAGE,
        "sort": "updated",
        "direction": "desc",
    }
    if since:
        params["since"] = _fmt_since(since)
    items: list[dict[str, Any]] = []
    page = 1
    async with httpx.AsyncClient(
        headers=_headers(token, use_global_token), timeout=30.0
    ) as client:
        while True:
            response = await client.get(
                f"{_GITHUB_API}/repos/{owner}/{repo}/issues",
                params={**params, "page": page},
            )
            if response.status_code in (401, 403, 404, 410):
                return []
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            items.extend(data)
            if len(data) < _PER_PAGE or (max_pages and page >= max_pages):
                break
            page += 1
    return items


async def _fetch_workflow_runs(
    owner: str,
    repo: str,
    since: datetime | None,
    *,
    token: str | None,
    use_global_token: bool,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"per_page": 50}
    if since:
        params["created"] = f">={_fmt_since(since)}"
    async with httpx.AsyncClient(
        headers=_headers(token, use_global_token), timeout=30.0
    ) as client:
        response = await client.get(
            f"{_GITHUB_API}/repos/{owner}/{repo}/actions/runs", params=params
        )
    if response.status_code in (401, 403, 404):
        return []
    response.raise_for_status()
    return response.json().get("workflow_runs", [])


async def _fetch_releases(
    owner: str,
    repo: str,
    since: datetime | None,
    *,
    token: str | None,
    use_global_token: bool,
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        headers=_headers(token, use_global_token), timeout=30.0
    ) as client:
        response = await client.get(
            f"{_GITHUB_API}/repos/{owner}/{repo}/releases", params={"per_page": 20}
        )
    if response.status_code in (401, 403, 404):
        return []
    response.raise_for_status()
    releases = response.json()
    if since:
        releases = [
            release
            for release in releases
            if release.get("published_at")
            and parse_github_timestamp(release["published_at"]) >= since
        ]
    return releases


async def fetch_github_activity(
    owner: str,
    repo: str,
    since: datetime | None = None,
    *,
    token: str | None = None,
    use_global_token: bool = True,
    trial_limits: bool = False,
) -> dict[str, Any]:
    max_pages = 1 if trial_limits else None
    commits_raw, issues_raw, workflows_raw, releases_raw = await asyncio.gather(
        fetch_commits_since(
            owner,
            repo,
            since,
            token=token,
            use_global_token=use_global_token,
            max_pages=max_pages,
        ),
        _fetch_issues_and_prs(
            owner,
            repo,
            since,
            token=token,
            use_global_token=use_global_token,
            max_pages=max_pages,
        ),
        _fetch_workflow_runs(
            owner, repo, since, token=token, use_global_token=use_global_token
        ),
        _fetch_releases(
            owner, repo, since, token=token, use_global_token=use_global_token
        ),
        return_exceptions=True,
    )

    commits: list[dict[str, Any]] = []
    if not isinstance(commits_raw, Exception):
        for commit in commits_raw:
            lines = commit.message.split("\n")
            commits.append(
                {
                    "sha": commit.sha,
                    "short_sha": commit.sha[:7],
                    "subject": lines[0],
                    "body": "\n".join(lines[1:]).strip(),
                    "author": commit.author_name,
                    "committed_at": commit.timestamp.isoformat() if commit.timestamp else "",
                }
            )
    else:
        raise commits_raw

    pull_requests: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if not isinstance(issues_raw, Exception):
        for item in issues_raw:
            labels = [label["name"] for label in item.get("labels", [])]
            if "pull_request" in item:
                pr = item["pull_request"]
                pull_requests.append(
                    {
                        "number": item["number"],
                        "title": item["title"],
                        "state": "merged" if pr.get("merged_at") else item["state"],
                        "author": (item.get("user") or {}).get("login", "unknown"),
                        "created_at": item.get("created_at", ""),
                        "closed_at": item.get("closed_at"),
                        "merged_at": pr.get("merged_at"),
                        "labels": labels,
                        "body": (item.get("body") or "")[:300],
                    }
                )
            else:
                issues.append(
                    {
                        "number": item["number"],
                        "title": item["title"],
                        "state": item["state"],
                        "author": (item.get("user") or {}).get("login", "unknown"),
                        "created_at": item.get("created_at", ""),
                        "closed_at": item.get("closed_at"),
                        "labels": labels,
                        "body": (item.get("body") or "")[:200],
                    }
                )

    workflow_runs: list[dict[str, Any]] = []
    if not isinstance(workflows_raw, Exception):
        for run in workflows_raw:
            workflow_runs.append(
                {
                    "name": run.get("name", ""),
                    "status": run.get("status", ""),
                    "conclusion": run.get("conclusion") or "in_progress",
                    "created_at": run.get("created_at", ""),
                    "branch": run.get("head_branch", ""),
                    "commit_subject": (run.get("head_commit") or {})
                    .get("message", "")
                    .split("\n")[0][:80],
                }
            )

    releases: list[dict[str, Any]] = []
    if not isinstance(releases_raw, Exception):
        for release in releases_raw:
            releases.append(
                {
                    "tag": release.get("tag_name", ""),
                    "name": release.get("name") or release.get("tag_name", ""),
                    "author": (release.get("author") or {}).get("login", "unknown"),
                    "published_at": release.get("published_at", ""),
                    "prerelease": release.get("prerelease", False),
                    "body": (release.get("body") or "")[:300],
                }
            )

    if trial_limits:
        commits = commits[:100]
        pull_requests = pull_requests[:50]
        issues = issues[:50]
        workflow_runs = workflow_runs[:30]
        releases = releases[:20]

    logger.info(
        "github_activity_fetched",
        repo=f"{owner}/{repo}",
        commits=len(commits),
        prs=len(pull_requests),
        issues=len(issues),
        workflows=len(workflow_runs),
        releases=len(releases),
        trial_limits=trial_limits,
    )
    return {
        "commits": commits,
        "pull_requests": pull_requests,
        "issues": issues,
        "workflow_runs": workflow_runs,
        "releases": releases,
    }
