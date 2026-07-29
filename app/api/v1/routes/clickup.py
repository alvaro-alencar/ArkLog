"""ClickUp APIs restricted to the ArkLog administrator credentials."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.v1.deps import require_admin
from app.integrations.clickup.client import ClickUpClient
from app.security.ark_auth import ArkIdentity

router = APIRouter()


@router.get("/teams")
async def list_clickup_teams(
    _: ArkIdentity = Depends(require_admin),
) -> list[dict[str, Any]]:
    client = ClickUpClient()
    try:
        teams = await client.get_teams()
        return [
            {"id": team["id"], "name": team["name"], "avatar": team.get("avatar")}
            for team in teams
        ]
    finally:
        await client.close()


@router.get("/teams/{team_id}/tasks")
async def list_clickup_tasks(
    team_id: str,
    _: ArkIdentity = Depends(require_admin),
) -> list[dict[str, Any]]:
    client = ClickUpClient()
    try:
        tasks = await client.get_tasks(team_id)
        return [
            {
                "id": task["id"],
                "name": task["name"],
                "status": task.get("status", {}).get("status"),
                "custom_id": task.get("custom_id"),
            }
            for task in tasks
        ]
    finally:
        await client.close()
