"""
ArkLog - GitHub Commit Parser

Transforms a raw GitHub push webhook payload into Commit domain entities.

GitHub push webhooks split file changes into three arrays (added / modified / removed).
We map each filename to a CommitFile with the appropriate status.

Note: Push webhooks do not include per-file diff counts (additions/deletions).
Those require a separate GitHub API call and will be added in Phase 3 if needed.
"""

from typing import Any

from app.domain.entities.commit import Commit, CommitFile
from app.utils.datetime_utils import parse_github_timestamp


class CommitParser:
    """Parses GitHub push event payloads into Commit domain entities."""

    def parse(self, payload: dict[str, Any]) -> list[Commit]:
        """
        Extract all commits from a push webhook payload.
        Returns an empty list for branch deletions or pushes with no commits.
        """
        repo_full_name = payload.get("repository", {}).get("full_name", "")
        ref = payload.get("ref", "")
        branch = ref.removeprefix("refs/heads/")

        raw_commits = payload.get("commits", [])
        if not raw_commits:
            return []

        return [
            self._parse_commit(raw, repo_full_name, branch)
            for raw in raw_commits
        ]

    def _parse_commit(
        self, raw: dict[str, Any], repo_full_name: str, branch: str
    ) -> Commit:
        author = raw.get("author", {})
        timestamp = parse_github_timestamp(raw.get("timestamp", "1970-01-01T00:00:00Z"))

        files: list[CommitFile] = []
        for filename in raw.get("added", []):
            files.append(CommitFile(filename=filename, status="added"))
        for filename in raw.get("modified", []):
            files.append(CommitFile(filename=filename, status="modified"))
        for filename in raw.get("removed", []):
            files.append(CommitFile(filename=filename, status="removed"))

        return Commit(
            sha=raw.get("id", ""),
            message=raw.get("message", ""),
            author_name=author.get("name", ""),
            author_email=author.get("email", ""),
            timestamp=timestamp,
            url=raw.get("url", ""),
            repo_full_name=repo_full_name,
            branch=branch,
            files=tuple(files),
        )
