"""User-owned connections for ArkLog sources and destinations."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select

from app.api.v1.deps import get_identity
from app.core.config import settings
from app.integrations.github.app_auth import (
    GitHubAppError,
    exchange_user_code,
    resolve_user_installation,
)
from app.integrations.runtime import IntegrationRuntimeError, list_connection_resources
from app.models.database import AsyncSessionLocal
from app.models.tables import AutomationFlowRecord, IntegrationConnectionRecord, UserRecord
from app.security.ark_auth import ArkIdentity
from app.security.credentials import encrypt_credentials
from app.security.oauth_state import OAuthStateError, create_oauth_state, decode_oauth_state
from app.utils.datetime_utils import naive_utcnow

router = APIRouter()
_ALLOWED = {"TRIAL", "ACTIVE"}


def _require_access(identity: ArkIdentity) -> None:
    if identity.access.status not in _ALLOWED:
        raise HTTPException(status_code=403, detail="Acesso ao ArkLog não autorizado.")


def _serialize(connection: IntegrationConnectionRecord) -> dict[str, Any]:
    return {
        "id": connection.id,
        "provider": connection.provider,
        "label": connection.label,
        "externalAccountId": connection.external_account_id,
        "externalAccountName": connection.external_account_name,
        "scopes": connection.scopes,
        "details": connection.details,
        "status": connection.status,
        "connectedAt": connection.connected_at.isoformat(),
        "updatedAt": connection.updated_at.isoformat(),
    }


async def _owned_connection(
    connection_id: int,
    identity: ArkIdentity,
) -> IntegrationConnectionRecord:
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session:
        connection = await session.scalar(
            select(IntegrationConnectionRecord).where(
                IntegrationConnectionRecord.id == connection_id,
                IntegrationConnectionRecord.user_id == identity.user.id,
                IntegrationConnectionRecord.organization_id == organization_id,
            )
        )
    if connection is None:
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    return connection


@router.get("")
async def list_connections(identity: ArkIdentity = Depends(get_identity)) -> dict[str, Any]:
    _require_access(identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(IntegrationConnectionRecord)
            .where(
                IntegrationConnectionRecord.user_id == identity.user.id,
                IntegrationConnectionRecord.organization_id == organization_id,
            )
            .order_by(IntegrationConnectionRecord.connected_at.desc())
        )
        connections = result.scalars().all()
    return {
        "connections": [_serialize(connection) for connection in connections],
        "providers": {
            "github": {"configured": settings.github_app_configured},
            "slack": {"configured": settings.slack_oauth_configured},
        },
    }


@router.get("/github/start")
async def start_github(identity: ArkIdentity = Depends(get_identity)) -> dict[str, str]:
    """Start a GitHub App installation where the user chooses repositories."""
    _require_access(identity)
    if not settings.github_app_configured:
        raise HTTPException(status_code=503, detail="GitHub App ainda não foi configurado.")
    organization_id = str(identity.ark_session["organization"]["id"])
    state_token = create_oauth_state("github", identity.user.id, organization_id)
    query = urlencode({"state": state_token})
    return {
        "authorizationUrl": (
            f"https://github.com/apps/{settings.github_app_slug}/installations/new?{query}"
        )
    }


@router.get("/github/setup")
async def github_setup(
    installation_id: int = Query(..., gt=0),
    state: str = Query(...),
    setup_action: str = Query(default="install"),
) -> RedirectResponse:
    """Receive the installation ID, sign it, then request GitHub user authorization."""
    if setup_action not in {"install", "update"}:
        raise HTTPException(status_code=400, detail="Ação de instalação GitHub inválida.")
    try:
        initial = decode_oauth_state(state, "github")
        authorization_state = create_oauth_state(
            "github",
            int(initial["user_id"]),
            str(initial["organization_id"]),
            extra={"installation_id": installation_id},
        )
    except OAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "state": authorization_state,
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")


@router.get("/github/callback")
async def github_callback(code: str = Query(...), state: str = Query(...)) -> RedirectResponse:
    """Verify the GitHub user and persist only the selected installation ID."""
    try:
        signed = decode_oauth_state(state, "github")
        installation_id = int(signed.get("installation_id") or 0)
        if installation_id <= 0:
            raise OAuthStateError("GitHub installation is missing from the signed state.")
        user_token = await exchange_user_code(code)
        installation = await resolve_user_installation(user_token, installation_id)
    except OAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GitHubAppError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    account = installation.get("account") or {}
    permissions = installation.get("permissions") or {}
    installation_value = int(installation.get("id") or 0)
    if installation_value <= 0:
        raise HTTPException(status_code=502, detail="GitHub não retornou uma instalação válida.")
    scopes = [
        f"{name}:{level}"
        for name, level in sorted(permissions.items())
        if str(level).lower() != "none"
    ]
    account_name = str(account.get("login") or account.get("name") or "GitHub")
    await _upsert_connection(
        user_id=int(signed["user_id"]),
        organization_id=str(signed["organization_id"]),
        provider="github",
        label=f"GitHub App · {account_name}",
        external_account_id=str(installation_value),
        external_account_name=account_name,
        credentials={"installation_id": installation_value},
        scopes=scopes,
        details={
            "accountId": account.get("id"),
            "accountType": account.get("type"),
            "avatarUrl": account.get("avatar_url"),
            "profileUrl": account.get("html_url"),
            "installationId": installation_value,
            "repositorySelection": installation.get("repository_selection"),
            "manageUrl": installation.get("html_url"),
        },
    )
    return RedirectResponse(
        f"{settings.public_app_url.rstrip('/')}/connections?connected=github"
    )


@router.get("/slack/start")
async def start_slack(identity: ArkIdentity = Depends(get_identity)) -> dict[str, str]:
    _require_access(identity)
    if not settings.slack_oauth_configured:
        raise HTTPException(status_code=503, detail="Slack OAuth ainda não foi configurado.")
    organization_id = str(identity.ark_session["organization"]["id"])
    state_token = create_oauth_state("slack", identity.user.id, organization_id)
    query = urlencode(
        {
            "client_id": settings.slack_client_id,
            "redirect_uri": settings.slack_redirect_uri,
            "scope": "channels:read,groups:read,chat:write",
            "state": state_token,
        }
    )
    return {"authorizationUrl": f"https://slack.com/oauth/v2/authorize?{query}"}


@router.get("/slack/callback")
async def slack_callback(code: str = Query(...), state: str = Query(...)) -> RedirectResponse:
    try:
        signed = decode_oauth_state(state, "slack")
    except OAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "code": code,
                "redirect_uri": settings.slack_redirect_uri,
            },
        )
    payload = response.json()
    if not response.is_success or not payload.get("ok") or not payload.get("access_token"):
        raise HTTPException(status_code=502, detail="Slack não concluiu a autorização.")
    team = payload.get("team") or {}
    authed_user = payload.get("authed_user") or {}
    scope = [
        item.strip()
        for item in str(payload.get("scope") or "").split(",")
        if item.strip()
    ]
    await _upsert_connection(
        user_id=int(signed["user_id"]),
        organization_id=str(signed["organization_id"]),
        provider="slack",
        label=f"Slack · {team.get('name') or team.get('id')}",
        external_account_id=str(team.get("id") or ""),
        external_account_name=str(team.get("name") or "Slack"),
        credentials={
            "bot_token": payload["access_token"],
            "bot_user_id": payload.get("bot_user_id"),
            "authed_user_id": authed_user.get("id"),
        },
        scopes=scope,
        details={"teamId": team.get("id"), "teamName": team.get("name")},
    )
    return RedirectResponse(
        f"{settings.public_app_url.rstrip('/')}/connections?connected=slack"
    )


@router.get("/{connection_id}/resources")
async def resources(
    connection_id: int,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    _require_access(identity)
    connection = await _owned_connection(connection_id, identity)
    if connection.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Reconecte esta conta antes de usá-la.")
    try:
        items = await list_connection_resources(connection)
    except IntegrationRuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"provider": connection.provider, "resources": items}


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    connection_id: int,
    identity: ArkIdentity = Depends(get_identity),
) -> None:
    _require_access(identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session, session.begin():
        connection = await session.scalar(
            select(IntegrationConnectionRecord).where(
                IntegrationConnectionRecord.id == connection_id,
                IntegrationConnectionRecord.user_id == identity.user.id,
                IntegrationConnectionRecord.organization_id == organization_id,
            )
        )
        if connection is None:
            raise HTTPException(status_code=404, detail="Conexão não encontrada.")
        dependent_flow = await session.scalar(
            select(AutomationFlowRecord.id)
            .where(
                AutomationFlowRecord.status != "ARCHIVED",
                or_(
                    AutomationFlowRecord.source_connection_id == connection.id,
                    AutomationFlowRecord.destination_connection_id == connection.id,
                ),
            )
            .limit(1)
        )
        if dependent_flow is not None:
            raise HTTPException(
                status_code=409,
                detail="Arquive os fluxos ativos que usam esta conexão antes de desconectá-la.",
            )
        await session.delete(connection)


async def _upsert_connection(
    *,
    user_id: int,
    organization_id: str,
    provider: str,
    label: str,
    external_account_id: str,
    external_account_name: str,
    credentials: dict[str, Any],
    scopes: list[str],
    details: dict[str, Any],
) -> None:
    async with AsyncSessionLocal() as session, session.begin():
        user = await session.get(UserRecord, user_id)
        if user is None or str(user.ark_organization_id) != organization_id:
            raise HTTPException(
                status_code=401,
                detail="A conta Ark da autorização não existe mais.",
            )
        connection = await session.scalar(
            select(IntegrationConnectionRecord).where(
                IntegrationConnectionRecord.user_id == user_id,
                IntegrationConnectionRecord.organization_id == organization_id,
                IntegrationConnectionRecord.provider == provider,
                IntegrationConnectionRecord.external_account_id == external_account_id,
            )
        )
        encrypted = encrypt_credentials(credentials)
        if connection is None:
            connection = IntegrationConnectionRecord(
                user_id=user_id,
                organization_id=organization_id,
                provider=provider,
                label=label,
                external_account_id=external_account_id,
                external_account_name=external_account_name,
                encrypted_credentials=encrypted,
                scopes=scopes,
                details=details,
                status="ACTIVE",
            )
            session.add(connection)
        else:
            connection.label = label
            connection.external_account_name = external_account_name
            connection.encrypted_credentials = encrypted
            connection.scopes = scopes
            connection.details = details
            connection.status = "ACTIVE"
            connection.updated_at = naive_utcnow()
