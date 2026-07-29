"""ArkLog session endpoint.

Application authentication is provided by the shared Ark account service.
GitHub OAuth is no longer accepted as an ArkLog login mechanism.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import get_identity
from app.security.access import public_access
from app.security.ark_auth import ArkIdentity

router = APIRouter()


@router.get("/session")
async def session(identity: ArkIdentity = Depends(get_identity)) -> dict:
    return {
        "user": {
            "id": identity.ark_session["user"]["id"],
            "name": identity.ark_session["user"].get("name"),
            "email": identity.ark_session["user"].get("email"),
            "isPlatformAdmin": identity.ark_session["user"].get("isPlatformAdmin", False),
        },
        "organization": identity.ark_session["organization"],
        "access": public_access(identity.access),
    }


@router.get("/login/github")
async def legacy_github_login() -> None:
    raise HTTPException(
        status_code=410,
        detail="Use e-mail e senha da conta Ark. O GitHub agora é somente uma integração de dados.",
    )


@router.get("/callback/github")
async def legacy_github_callback() -> None:
    raise HTTPException(status_code=410, detail="Fluxo antigo de autenticação desativado.")
