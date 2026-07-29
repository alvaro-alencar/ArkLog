"""Retired ClickUp endpoints from the pre-connection architecture."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _retired() -> None:
    raise HTTPException(
        status_code=410,
        detail=(
            "A integração global do ClickUp foi desativada. "
            "ClickUp retornará como uma conexão pertencente ao usuário."
        ),
    )


@router.get("/teams")
async def list_clickup_teams() -> None:
    _retired()


@router.get("/teams/{team_id}/tasks")
async def list_clickup_tasks(team_id: str) -> None:
    del team_id
    _retired()
