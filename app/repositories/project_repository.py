"""
ArkLog - Project Repository

Syncs project domain entities (from projects.yaml) into the database.
The get_or_create pattern ensures a DB record exists for every configured
project without requiring manual migration steps.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.project import Project
from app.models.tables import ProjectRecord
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[ProjectRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectRecord)

    async def get_or_create(self, project: Project) -> ProjectRecord:
        """Return existing DB record or create one. Safe to call multiple times."""
        result = await self._session.execute(
            select(ProjectRecord).where(ProjectRecord.name == project.name).limit(1)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = ProjectRecord(
                name=project.name,
                repo_full_name=project.repo_full_name,
                clickup_task_id=project.clickup_task_id,
            )
            record = await self.add(record)
        return record
