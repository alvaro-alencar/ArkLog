"""
ArkLog - Report Repository

Persistence queries for ReportRecord with timeline and pagination support.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import ReportRecord
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[ReportRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReportRecord)

    async def get_by_project(
        self, project_id: int, limit: int = 20, offset: int = 0
    ) -> list[ReportRecord]:
        result = await self._session.execute(
            select(ReportRecord)
            .where(ReportRecord.project_id == project_id)
            .order_by(ReportRecord.generated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_project(self, project_id: int) -> int:
        result = await self._session.execute(
            select(func.count(ReportRecord.id)).where(
                ReportRecord.project_id == project_id
            )
        )
        return result.scalar_one() or 0

    async def get_latest(self, project_id: int) -> Optional[ReportRecord]:
        result = await self._session.execute(
            select(ReportRecord)
            .where(ReportRecord.project_id == project_id)
            .order_by(ReportRecord.generated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, report_id: int) -> Optional[ReportRecord]:
        return await self._session.get(ReportRecord, report_id)

    async def get_since(self, project_id: int, since: datetime) -> list[ReportRecord]:
        result = await self._session.execute(
            select(ReportRecord)
            .where(
                ReportRecord.project_id == project_id,
                ReportRecord.generated_at >= since,
            )
            .order_by(ReportRecord.generated_at.asc())
        )
        return list(result.scalars().all())
