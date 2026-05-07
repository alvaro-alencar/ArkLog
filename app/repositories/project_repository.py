"""
ArkLog - Project Repository

Handles persistence and retrieval of ProjectRecord.
Now the source of truth for all project configurations.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tables import ProjectRecord
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[ProjectRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectRecord)

    async def get_by_name(self, name: str) -> Optional[ProjectRecord]:
        result = await self._session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.name == name)
            .options(selectinload(ProjectRecord.destinations))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_repo(self, repo_full_name: str) -> Optional[ProjectRecord]:
        """Find a project by its GitHub repository name."""
        result = await self._session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.repo_full_name == repo_full_name)
            .options(selectinload(ProjectRecord.destinations))
        )
        # There might be multiple projects using the same repo for different users?
        # For now, return the first one found or we should filter by user.
        return result.scalars().first()

    async def get_all_active(self) -> list[ProjectRecord]:
        """List all projects with their destinations for the scheduler."""
        result = await self._session.execute(
            select(ProjectRecord).options(selectinload(ProjectRecord.destinations))
        )
        return list(result.scalars().all())
