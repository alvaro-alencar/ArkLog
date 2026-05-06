"""
ArkLog - GitHub Commit Parser

Transforms a raw GitHub push webhook payload into typed Commit entities.

Notes on GitHub push payload structure:
- `commits` array contains individual commit objects
- Files are split into `added`, `modified`, `removed` arrays (filenames only)
- Full diff counts require a separate API call — not available in webhooks
- Branch extracted by stripping the "refs/heads/" prefix from `ref`
"""

from datetime import datetime
from typing import Any

import structlog

from app.domain.entities.commit import Commit, CommitFile
from app.utils.datetime_utils import parse_github_timestamp

logger = structlog.get_logger(__name__)


class CommitParser:
    """Parses GitHub push webhook payloads into Commit domain entities."""

    def parse(self, payload: dict[str, Any]) -> list[Commit]:
        """
        Extract a list of Commit entities from a push webhook payload.
        Returns an empty list for payloads with no commits (e.g. tag pushes).
        """
        repo_full_name = payload.get("repository", {}).get("full_name", "")
        branch = self._extract_branch(payload.get("ref", ""))
        raw_commits = payload.get("commits", [])

        if not raw_commits:
            logger.debug("commit_parser_no_commits", repo=repo_full_name, branch=branch)
            return []

        commits = []
        for raw in raw_commits:
            try:
                commits.append(self._parse_single(raw, repo_full_name, branch))
            except Exception as exc:
                logger.error(
                    "commit_parse_error",
                    sha=raw.get("id", "?"),
                    error=str(exc),
                )

        logger.info(
            "commits_parsed",
            repo=repo_full_name,
            branch=branch,
            count=len(commits),
        )
        return commits

    def _parse_single(
        self, raw: dict[str, Any], repo_full_name: str, branch: str
    ) -> Commit:
        sha = raw["id"]
        files = self._parse_files(raw)
        timestamp = parse_github_timestamp(raw["timestamp"])

        return Commit(
            sha=sha,
            message=raw.get("message", ""),
            author_name=raw.get("author", {}).get("name", ""),
            author_email=raw.get("author", {}).get("email", ""),
            timestamp=timestamp,
            url=raw.get("url", ""),
            repo_full_name=repo_full_name,
            branch=branch,
            files=tuple(files),
        )

    def _parse_files(self, raw: dict[str, Any]) -> list[CommitFile]:
        files = []
        for filename in raw.get("added", []):
            files.append(CommitFile(filename=filename, status="added"))
        for filename in raw.get("modified", []):
            files.append(CommitFile(filename=filename, status="modified"))
        for filename in raw.get("removed", []):
            files.append(CommitFile(filename=filename, status="removed"))
        return files

    @staticmethod
    def _extract_branch(ref: str) -> str:
        """Strip 'refs/heads/' prefix from a git ref string."""
        prefix = "refs/heads/"
        return ref[len(prefix):] if ref.startswith(prefix) else ref
