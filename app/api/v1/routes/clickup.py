"""
ArkLog - ClickUp Integration APIs

Proxies requests to the ClickUp API.
Used by the Dashboard to list teams and tasks.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.api.v1.deps import get_current_user
from app.integrations.clickup.client import ClickUpClient
from app.models.tables import UserRecord

router = APIRouter()


@router.get("/teams")
async def list_clickup_teams(
    current_user: UserRecord = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all ClickUp teams (workspaces) the user has access to."""
    client = ClickUpClient()
    try:
        teams = await client.get_teams()
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "avatar": t.get("avatar"),
            }
            for t in teams
        ]
    finally:
        await client.close()


@router.get("/teams/{team_id}/tasks")
async def list_clickup_tasks(
    team_id: str,
    current_user: UserRecord = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List tasks in a ClickUp team."""
    client = ClickUpClient()
    try:
        tasks = await client.get_tasks(team_id)
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "status": t.get("status", {}).get("status"),
                "custom_id": t.get("custom_id"),
            }
            for t in tasks
        ]
    finally:
        await client.close()
