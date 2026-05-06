"""
ArkLog - Commit Repository

Persists and queries Commit records. Extends BaseRepository with
commit-specific queries needed by CommitService and the scheduler.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.commit import Commit
from app.models.tables import CommitRecord
from app.repositories.base import BaseRepository


class CommitRepository(BaseRepository[CommitRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CommitRecord)

    async def exists(self, sha: str) -> bool:
        """Check if a commit was already processed (idempotency guard)."""
        result = await self._session.execute(
            select(CommitRecord.id).where(CommitRecord.sha == sha).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def save_commit(self, commit: Commit, project_id: int) -> CommitRecord:
        """Persist a Commit entity linked to a project."""
        record = CommitRecord(
            sha=commit.sha,
            message=commit.message,
            author_name=commit.author_name,
            author_email=commit.author_email,
            committed_at=commit.timestamp,
            branch=commit.branch,
            files_changed=len(commit.files),
            project_id=project_id,
        )
        return await self.add(record)

    async def get_since(
        self, project_id: int, since: datetime
    ) -> list[CommitRecord]:
        """Return all commits for a project after a given datetime."""
        result = await self._session.execute(
            select(CommitRecord)
            .where(
                CommitRecord.project_id == project_id,
                CommitRecord.committed_at >= since,
            )
            .order_by(CommitRecord.committed_at.asc())
        )
        return list(result.scalars().all())
