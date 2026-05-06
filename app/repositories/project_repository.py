"""
ArkLog - Project Repository

Persists project records and synchronizes them with projects.yaml.
The get_or_create pattern ensures projects.yaml is always the source
of truth while maintaining a stable DB identity for foreign keys.
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
        """
        Return the existing ProjectRecord or create a new one.
        Called each time a push event arrives to ensure the project
        exists in the DB before linking commits to it.
        """
        result = await self._session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.name == project.name)
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        return await self.add(
            ProjectRecord(
                name=project.name,
                repo_full_name=project.repo_full_name,
                clickup_task_id=project.clickup_task_id,
            )
        )
