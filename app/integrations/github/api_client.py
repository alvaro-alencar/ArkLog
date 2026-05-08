"""
ArkLog - GitHub REST API Client

Fetches commit history for backfill operations.
Uses Personal Access Token if configured (required for private repos).
Rate limit: 60 req/h unauthenticated, 5000 req/h with token.
"""

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


async def fetch_commits_since(owner: str, repo: str, since: "datetime | None" = None) -> list[Commit]:
    """Fetch commits since a specific datetime (or all if since=None)."""
    from datetime import datetime  # noqa: F811
    commits: list[Commit] = []
    repo_full_name = f"{owner}/{repo}"
    page = 1
    params: dict = {"per_page": _PER_PAGE}
    if since:
        params["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

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
    """
    Fetch every commit in a repository via the GitHub API (paginated).
    Files are not available from the list endpoint — files_changed defaults to 0.
    """
    commits: list[Commit] = []
    repo_full_name = f"{owner}/{repo}"
    page = 1

    async with httpx.AsyncClient(headers=_headers(), timeout=30.0) as client:
        while True:
            response = await client.get(
                f"{_GITHUB_API}/repos/{owner}/{repo}/commits",
                params={"per_page": _PER_PAGE, "page": page},
            )

            if response.status_code == 401:
                raise RuntimeError(
                    f"GitHub API returned 401 for {repo_full_name}. "
                    "Set GITHUB_TOKEN in .env for private repositories."
                )
            if response.status_code == 404:
                raise RuntimeError(
                    f"Repository {repo_full_name} not found or no access. "
                    "Check repo name and GITHUB_TOKEN permissions."
                )
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

            logger.debug(
                "github_api_commits_page",
                repo=repo_full_name,
                page=page,
                count=len(items),
            )

            if len(items) < _PER_PAGE:
                break
            page += 1

    logger.info("github_api_commits_fetched", repo=repo_full_name, total=len(commits))
    return commits
