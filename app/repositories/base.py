"""
ArkLog - Base Repository

Generic async repository with common CRUD operations.
Concrete repositories extend this for entity-specific queries.

Follows the Repository pattern (DDD): domain logic is unaware of
how or where data is stored.
"""

from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic async CRUD repository.

    Usage:
        class ReportRepository(BaseRepository[ReportRecord]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, ReportRecord)
    """

    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, record_id: int) -> Optional[T]:
        return await self._session.get(self._model, record_id)

    async def get_all(self) -> list[T]:
        result = await self._session.execute(select(self._model))
        return list(result.scalars().all())

    async def add(self, record: T) -> T:
        self._session.add(record)
        await self._session.flush()
        return record

    async def delete(self, record: T) -> None:
        await self._session.delete(record)
        await self._session.flush()

    async def filter_by(self, **kwargs: Any) -> list[T]:
        stmt = select(self._model).filter_by(**kwargs)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
