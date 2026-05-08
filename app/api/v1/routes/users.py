"""ArkLog - User preferences endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import update

from app.api.v1.deps import get_current_user
from app.models.database import AsyncSessionLocal
from app.models.tables import UserRecord

router = APIRouter()


class UserPrefsUpdate(BaseModel):
    timezone: str | None = None
    language: str | None = None


@router.patch("/me")
async def update_user_prefs(
    data: UserPrefsUpdate,
    current_user: UserRecord = Depends(get_current_user),
) -> dict:
    """Persist language and timezone preferences for the authenticated user."""
    updates: dict = {}
    if data.timezone:
        updates["timezone"] = data.timezone
    if data.language:
        updates["language"] = data.language

    if updates:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(UserRecord)
                    .where(UserRecord.id == current_user.id)
                    .values(**updates)
                )

    return {"status": "ok", **updates}
