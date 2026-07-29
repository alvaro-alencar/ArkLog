"""GitHub source APIs without exposing the owner's token."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import get_identity
from app.core.config import settings
from app.security.ark_auth import ArkIdentity

router = APIRouter()


@router.get("/repos")
async def list_user_repos(
    identity: ArkIdentity = Depends(get_identity),
) -> list[dict[str, Any]]:
    if identity.access.status not in {"TRIAL", "ACTIVE"}:
        raise HTTPException(status_code=403, detail="Acesso ao ArkLog não autorizado.")

    token = identity.user.github_access_token
    if not token and identity.access.is_admin:
        token = settings.github_token
    if not token:
        return []

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            params={"sort": "updated", "per_page": 100},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    if response.status_code in {401, 403}:
        raise HTTPException(status_code=502, detail="A integração GitHub precisa ser reconectada.")
    response.raise_for_status()
    return [
        {
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "private": repo["private"],
            "description": repo.get("description"),
            "html_url": repo["html_url"],
        }
        for repo in response.json()
    ]
