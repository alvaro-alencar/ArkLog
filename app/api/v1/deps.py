"""FastAPI authentication and authorization dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.tables import ArkLogAccessRecord, UserRecord
from app.security.ark_auth import ArkIdentity, resolve_identity

bearer_scheme = HTTPBearer(auto_error=False)


async def get_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> ArkIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Entre na sua conta Ark para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await resolve_identity(credentials.credentials)


async def get_authenticated_user(identity: ArkIdentity = Depends(get_identity)) -> UserRecord:
    return identity.user


async def get_current_user(identity: ArkIdentity = Depends(get_identity)) -> UserRecord:
    if identity.access.status not in {"TRIAL", "ACTIVE"}:
        detail = (
            "Acesso ao ArkLog ainda não foi liberado."
            if identity.access.status == "PENDING"
            else "Acesso ao ArkLog bloqueado."
        )
        raise HTTPException(status_code=403, detail=detail)
    return identity.user


async def get_current_access(identity: ArkIdentity = Depends(get_identity)) -> ArkLogAccessRecord:
    if identity.access.status not in {"TRIAL", "ACTIVE"}:
        raise HTTPException(status_code=403, detail="Acesso ao ArkLog não autorizado.")
    return identity.access


async def require_active_access(identity: ArkIdentity = Depends(get_identity)) -> ArkIdentity:
    if identity.access.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Este recurso exige acesso completo ao ArkLog.",
        )
    return identity


async def require_admin(identity: ArkIdentity = Depends(get_identity)) -> ArkIdentity:
    if not identity.access.is_admin:
        raise HTTPException(status_code=403, detail="Área exclusiva da administração ArkLog.")
    return identity
