"""
ArkLog - Commit Entity

Immutable representation of a git commit extracted from a GitHub push event.
This is the core unit of analysis for the entire ArkLog pipeline.

Immutability (frozen=True) guarantees that once a commit is parsed from a
webhook payload, its data cannot be accidentally mutated during processing.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CommitFile:
    """A single file changed within a commit."""

    filename: str
    status: str  # added | modified | removed | renamed
    additions: int = 0
    deletions: int = 0
    patch: str = ""

    @property
    def extension(self) -> str:
        return self.filename.rsplit(".", 1)[-1] if "." in self.filename else ""

    @property
    def directory(self) -> str:
        parts = self.filename.rsplit("/", 1)
        return parts[0] if len(parts) > 1 else "."

    @property
    def net_changes(self) -> int:
        return self.additions - self.deletions


@dataclass(frozen=True)
class Commit:
    """
    Immutable git commit representation.

    Populated by the GitHub webhook parser (Phase 2) from raw push event
    payloads. Used downstream by the AI engine for semantic analysis.
    """

    sha: str
    message: str
    author_name: str
    author_email: str
    timestamp: datetime
    url: str
    repo_full_name: str
    branch: str
    files: tuple[CommitFile, ...] = field(default_factory=tuple)

    @property
    def short_sha(self) -> str:
        return self.sha[:7]

    @property
    def subject(self) -> str:
        """First line of the commit message."""
        return self.message.split("\n")[0]

    @property
    def total_changes(self) -> int:
        return sum(f.additions + f.deletions for f in self.files)

    @property
    def affected_directories(self) -> set[str]:
        return {f.directory for f in self.files}

    @property
    def affected_extensions(self) -> set[str]:
        return {f.extension for f in self.files if f.extension}

    @property
    def is_merge_commit(self) -> bool:
        return self.message.startswith("Merge")
