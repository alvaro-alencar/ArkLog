"""
ArkLog - GitHub Integration APIs

Proxies requests to the GitHub API using the user's OAuth token.
Used by the Dashboard to list repositories and setup webhooks.
"""

import httpx
from fastapi import APIRouter, Depends
from typing import Any

from app.api.v1.deps import get_current_user
from app.models.tables import UserRecord

router = APIRouter()


@router.get("/repos")
async def list_user_repos(
    current_user: UserRecord = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all repositories the user has access to."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            params={"sort": "updated", "per_page": 100},
            headers={"Authorization": f"token {current_user.github_access_token}"},
        )
        resp.raise_for_status()
        repos = resp.json()
    
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "full_name": r["full_name"],
            "private": r["private"],
            "description": r["description"],
            "html_url": r["html_url"],
        }
        for r in repos
    ]
