"""Retired GitHub endpoint from the pre-connection architecture."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/repos")
async def list_user_repos() -> None:
    raise HTTPException(
        status_code=410,
        detail=(
            "Use Conexões → GitHub e consulte os repositórios pela conexão escolhida. "
            "O ArkLog não usa mais token pessoal salvo no perfil nem credencial administrativa."
        ),
    )
