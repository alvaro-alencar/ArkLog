"""Authentication against the shared Ark account service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.models.tables import ArkLogAccessRecord, UserRecord
from app.utils.datetime_utils import naive_utcnow


@dataclass(frozen=True)
class ArkIdentity:
    user: UserRecord
    access: ArkLogAccessRecord
    ark_session: dict[str, Any]
    token: str


def _synthetic_github_id(ark_user_id: str) -> int:
    raw = hashlib.sha256(ark_user_id.encode("utf-8")).digest()[:8]
    return int.from_bytes(raw, "big") & ((1 << 63) - 1)


async def introspect_ark_session(token: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=settings.ark_auth_timeout_seconds) as client:
            response = await client.get(
                settings.ark_auth_me_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Ark-SaaS-Client": "1",
                    "User-Agent": "ArkLog/0.2",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível validar a conta Ark agora.",
        ) from exc

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Sessão Ark inválida ou expirada.")
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="Serviço de identidade Ark indisponível.")

    payload = response.json()
    if not payload.get("user", {}).get("id") or not payload.get("organization", {}).get("id"):
        raise HTTPException(status_code=401, detail="Sessão Ark incompleta.")
    return payload


async def resolve_identity(token: str) -> ArkIdentity:
    ark_session = await introspect_ark_session(token)
    ark_user = ark_session["user"]
    ark_org = ark_session["organization"]
    ark_user_id = str(ark_user["id"])
    email = str(ark_user.get("email") or "").strip().lower()
    is_admin = bool(ark_user.get("isPlatformAdmin")) or email in settings.admin_email_set

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(UserRecord).where(UserRecord.ark_user_id == ark_user_id)
            )
            user = result.scalar_one_or_none()
            if user is None and email:
                result = await session.execute(select(UserRecord).where(UserRecord.email == email))
                user = result.scalar_one_or_none()

            if user is None:
                user = UserRecord(
                    github_id=_synthetic_github_id(ark_user_id),
                    username=email or f"ark-{ark_user_id[:12]}",
                    email=email or None,
                    avatar_url=None,
                    github_access_token="",
                    ark_user_id=ark_user_id,
                    ark_organization_id=str(ark_org["id"]),
                    is_platform_admin=is_admin,
                )
                session.add(user)
                await session.flush()
            else:
                user.ark_user_id = ark_user_id
                user.ark_organization_id = str(ark_org["id"])
                user.email = email or user.email
                user.username = email or user.username
                user.is_platform_admin = is_admin

            access_result = await session.execute(
                select(ArkLogAccessRecord).where(ArkLogAccessRecord.user_id == user.id)
            )
            access = access_result.scalar_one_or_none()
            if access is None:
                if is_admin:
                    access = ArkLogAccessRecord(
                        user_id=user.id,
                        status="ACTIVE",
                        report_limit=-1,
                        reports_used=0,
                        is_admin=True,
                        approved_at=naive_utcnow(),
                    )
                elif settings.arklog_auto_trial:
                    now = naive_utcnow()
                    access = ArkLogAccessRecord(
                        user_id=user.id,
                        status="TRIAL",
                        report_limit=1,
                        reports_used=0,
                        is_admin=False,
                        approved_at=now,
                        trial_granted_at=now,
                    )
                else:
                    access = ArkLogAccessRecord(user_id=user.id, status="PENDING")
                session.add(access)
                await session.flush()
            elif is_admin and (not access.is_admin or access.status != "ACTIVE"):
                access.is_admin = True
                access.status = "ACTIVE"
                access.report_limit = -1
                access.approved_at = access.approved_at or naive_utcnow()
                access.blocked_reason = None

        await session.refresh(user)
        await session.refresh(access)

    return ArkIdentity(user=user, access=access, ark_session=ark_session, token=token)
