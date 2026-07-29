"""ArkLog product access administration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_identity, require_admin
from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.models.tables import ArkLogAccessRecord, UserRecord
from app.security.access import public_access
from app.security.ark_auth import ArkIdentity
from app.utils.datetime_utils import naive_utcnow

router = APIRouter()


def _serialize(user: UserRecord, access: ArkLogAccessRecord) -> dict:
    return {
        "localUserId": user.id,
        "arkUserId": user.ark_user_id,
        "name": user.username,
        "email": user.email,
        "createdAt": user.created_at.isoformat(),
        "access": public_access(access),
    }


@router.get("/me")
async def my_access(identity: ArkIdentity = Depends(get_identity)) -> dict:
    return {
        "user": {
            "id": identity.ark_session["user"]["id"],
            "name": identity.ark_session["user"].get("name"),
            "email": identity.ark_session["user"].get("email"),
        },
        "organization": identity.ark_session["organization"],
        "access": public_access(identity.access),
    }


@router.get("/admin/users")
async def list_accesses(_: ArkIdentity = Depends(require_admin)) -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserRecord)
            .options(selectinload(UserRecord.arklog_access))
            .where(UserRecord.ark_user_id.is_not(None))
            .order_by(UserRecord.created_at.desc())
        )
        users = result.scalars().all()
    return {
        "users": [
            _serialize(user, user.arklog_access)
            for user in users
            if user.arklog_access is not None
        ]
    }


async def _change_access(user_id: int, action: str) -> dict:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(UserRecord)
                .options(selectinload(UserRecord.arklog_access))
                .where(UserRecord.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user or not user.arklog_access:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")
            access = user.arklog_access
            if access.is_admin and action == "block":
                raise HTTPException(
                    status_code=400,
                    detail="Administrador não pode ser bloqueado por esta rota.",
                )

            if action == "trial":
                if access.trial_granted_at is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="O relatório gratuito já foi concedido a este usuário.",
                    )
                now = naive_utcnow()
                access.status = "TRIAL"
                access.report_limit = 1
                access.reports_used = 0
                access.approved_at = now
                access.trial_granted_at = now
                access.blocked_reason = None
            elif action == "activate":
                access.status = "ACTIVE"
                access.report_limit = settings.arklog_active_report_limit
                access.approved_at = naive_utcnow()
                access.blocked_reason = None
            elif action == "block":
                access.status = "BLOCKED"
                access.report_limit = 0
                access.blocked_reason = "Bloqueado pela administração."
            else:
                raise HTTPException(status_code=400, detail="Ação inválida.")
        await session.refresh(access)
        return _serialize(user, access)


@router.post("/admin/users/{user_id}/grant-trial")
async def grant_trial(user_id: int, _: ArkIdentity = Depends(require_admin)) -> dict:
    return await _change_access(user_id, "trial")


@router.post("/admin/users/{user_id}/activate")
async def activate(user_id: int, _: ArkIdentity = Depends(require_admin)) -> dict:
    return await _change_access(user_id, "activate")


@router.post("/admin/users/{user_id}/block")
async def block(user_id: int, _: ArkIdentity = Depends(require_admin)) -> dict:
    return await _change_access(user_id, "block")
