"""
ArkLog - GitHub REST API Client

Fetches full project activity: commits, PRs, issues, CI workflow runs, releases.
Uses Personal Access Token if configured (required for private repos and Actions API).
Rate limit: 60 req/h unauthenticated, 5000 req/h with token.
"""

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


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _fmt_since(since: datetime) -> str:
    return since.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Commits
# ---------------------------------------------------------------------------

async def fetch_commits_since(owner: str, repo: str, since: datetime | None = None) -> list[Commit]:
    """Fetch commits since a specific datetime (or all if since=None)."""
    commits: list[Commit] = []
    repo_full_name = f"{owner}/{repo}"
    page = 1
    params: dict = {"per_page": _PER_PAGE}
    if since:
        params["since"] = _fmt_since(since)

    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        while True:
            response = await client.get(
                f"{_GITHUB_API}/repos/{owner}/{repo}/commits",
                params={**params, "page": page},
            )
            if response.status_code == 401:
                raise RuntimeError(f"GitHub API 401 for {repo_full_name}. Set GITHUB_TOKEN for private repos.")
            if response.status_code == 404:
                raise RuntimeError(f"Repository {repo_full_name} not found.")
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
                        repo_full_name=repo_full_name,
                        branch="",
                        files=(),
                    )
                )

            if len(items) < _PER_PAGE:
                break
            page += 1

    logger.info("github_api_commits_fetched", repo=repo_full_name, total=len(commits), since=since)
    return commits


async def fetch_all_commits(owner: str, repo: str) -> list[Commit]:
    """Fetch every commit in a repository (paginated). Used for backfill."""
    return await fetch_commits_since(owner, repo, since=None)


# ---------------------------------------------------------------------------
# Pull Requests & Issues  (GitHub issues endpoint returns both)
# ---------------------------------------------------------------------------

async def _fetch_issues_and_prs(owner: str, repo: str, since: datetime | None) -> list[dict[str, Any]]:
    params: dict = {"state": "all", "per_page": _PER_PAGE, "sort": "updated", "direction": "desc"}
    if since:
        params["since"] = _fmt_since(since)

    items: list[dict] = []
    page = 1
    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        while True:
            r = await client.get(
                f"{_GITHUB_API}/repos/{owner}/{repo}/issues",
                params={**params, "page": page},
            )
            if r.status_code in (401, 403, 404, 410):
                logger.debug("github_issues_unavailable", status=r.status_code, repo=f"{owner}/{repo}")
                return []
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            items.extend(data)
            if len(data) < _PER_PAGE:
                break
            page += 1
    return items


# ---------------------------------------------------------------------------
# CI / Workflow runs
# ---------------------------------------------------------------------------

async def _fetch_workflow_runs(owner: str, repo: str, since: datetime | None) -> list[dict[str, Any]]:
    params: dict = {"per_page": 50}
    if since:
        params["created"] = f">={_fmt_since(since)}"

    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        r = await client.get(
            f"{_GITHUB_API}/repos/{owner}/{repo}/actions/runs",
            params=params,
        )
        if r.status_code in (401, 403, 404):
            logger.debug("github_actions_unavailable", status=r.status_code, repo=f"{owner}/{repo}")
            return []
        r.raise_for_status()
        return r.json().get("workflow_runs", [])


# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------

async def _fetch_releases(owner: str, repo: str, since: datetime | None) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        r = await client.get(
            f"{_GITHUB_API}/repos/{owner}/{repo}/releases",
            params={"per_page": 20},
        )
        if r.status_code in (401, 403, 404):
            return []
        r.raise_for_status()
        releases = r.json()

    if since:
        releases = [
            rel for rel in releases
            if rel.get("published_at") and parse_github_timestamp(rel["published_at"]) >= since
        ]
    return releases


# ---------------------------------------------------------------------------
# Unified activity fetch
# ---------------------------------------------------------------------------

async def fetch_github_activity(
    owner: str, repo: str, since: datetime | None = None
) -> dict[str, Any]:
    """
    Fetch all relevant GitHub activity in parallel.
    Returns a structured dict ready for the AI context builder.
    """
    commits_raw, issues_prs_raw, workflows_raw, releases_raw = await asyncio.gather(
        fetch_commits_since(owner, repo, since),
        _fetch_issues_and_prs(owner, repo, since),
        _fetch_workflow_runs(owner, repo, since),
        _fetch_releases(owner, repo, since),
        return_exceptions=True,
    )

    # --- Commits ---
    commits: list[dict] = []
    if not isinstance(commits_raw, Exception):
        for c in commits_raw:
            lines = c.message.split("\n")
            commits.append({
                "sha": c.sha,
                "short_sha": c.sha[:7],
                "subject": lines[0],
                "body": "\n".join(lines[1:]).strip(),
                "author": c.author_name,
                "committed_at": c.timestamp.isoformat() if c.timestamp else "",
            })
    elif isinstance(commits_raw, Exception):
        logger.warning("fetch_commits_failed", error=str(commits_raw))

    # --- PRs and Issues ---
    pull_requests: list[dict] = []
    issues: list[dict] = []
    if not isinstance(issues_prs_raw, Exception):
        for item in issues_prs_raw:
            labels = [lbl["name"] for lbl in item.get("labels", [])]
            if "pull_request" in item:
                pr = item["pull_request"]
                pull_requests.append({
                    "number": item["number"],
                    "title": item["title"],
                    "state": "merged" if pr.get("merged_at") else item["state"],
                    "author": (item.get("user") or {}).get("login", "unknown"),
                    "created_at": item.get("created_at", ""),
                    "closed_at": item.get("closed_at"),
                    "merged_at": pr.get("merged_at"),
                    "labels": labels,
                    "body": (item.get("body") or "")[:300],
                })
            else:
                issues.append({
                    "number": item["number"],
                    "title": item["title"],
                    "state": item["state"],
                    "author": (item.get("user") or {}).get("login", "unknown"),
                    "created_at": item.get("created_at", ""),
                    "closed_at": item.get("closed_at"),
                    "labels": labels,
                    "body": (item.get("body") or "")[:200],
                })
    elif isinstance(issues_prs_raw, Exception):
        logger.warning("fetch_issues_prs_failed", error=str(issues_prs_raw))

    # --- Workflow runs ---
    workflow_runs: list[dict] = []
    if not isinstance(workflows_raw, Exception):
        for run in workflows_raw:
            workflow_runs.append({
                "name": run.get("name", ""),
                "status": run.get("status", ""),
                "conclusion": run.get("conclusion") or "in_progress",
                "created_at": run.get("created_at", ""),
                "branch": run.get("head_branch", ""),
                "commit_subject": (run.get("head_commit") or {}).get("message", "").split("\n")[0][:80],
            })
    elif isinstance(workflows_raw, Exception):
        logger.warning("fetch_workflows_failed", error=str(workflows_raw))

    # --- Releases ---
    releases: list[dict] = []
    if not isinstance(releases_raw, Exception):
        for rel in releases_raw:
            releases.append({
                "tag": rel.get("tag_name", ""),
                "name": rel.get("name") or rel.get("tag_name", ""),
                "author": (rel.get("author") or {}).get("login", "unknown"),
                "published_at": rel.get("published_at", ""),
                "prerelease": rel.get("prerelease", False),
                "body": (rel.get("body") or "")[:300],
            })
    elif isinstance(releases_raw, Exception):
        logger.warning("fetch_releases_failed", error=str(releases_raw))

    logger.info(
        "github_activity_fetched",
        repo=f"{owner}/{repo}",
        commits=len(commits),
        prs=len(pull_requests),
        issues=len(issues),
        workflows=len(workflow_runs),
        releases=len(releases),
    )

    return {
        "commits": commits,
        "pull_requests": pull_requests,
        "issues": issues,
        "workflow_runs": workflow_runs,
        "releases": releases,
    }
