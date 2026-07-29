"""User-owned OAuth connections for ArkLog sources and destinations."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select

from app.api.v1.deps import get_identity
from app.core.config import settings
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
            "github": {
                "configured": bool(
                    settings.github_client_id and settings.github_client_secret
                )
            },
            "slack": {
                "configured": bool(
                    settings.slack_client_id and settings.slack_client_secret
                )
            },
        },
    }


@router.get("/github/start")
async def start_github(identity: ArkIdentity = Depends(get_identity)) -> dict[str, str]:
    _require_access(identity)
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth ainda não foi configurado.")
    organization_id = str(identity.ark_session["organization"]["id"])
    state_token = create_oauth_state("github", identity.user.id, organization_id)
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "read:user user:email repo",
            "state": state_token,
            "allow_signup": "true",
        }
    )
    return {"authorizationUrl": f"https://github.com/login/oauth/authorize?{query}"}


@router.get("/github/callback")
async def github_callback(code: str = Query(...), state: str = Query(...)) -> RedirectResponse:
    try:
        signed = decode_oauth_state(state, "github")
    except OAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with httpx.AsyncClient(timeout=25.0) as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
        )
        token_payload = token_response.json()
        access_token = str(token_payload.get("access_token") or "")
        if not token_response.is_success or not access_token:
            raise HTTPException(status_code=502, detail="GitHub não concluiu a autorização.")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ArkLog/0.3",
        }
        profile_response = await client.get(
            f"{settings.github_api_base_url}/user", headers=headers
        )
        if not profile_response.is_success:
            raise HTTPException(status_code=502, detail="GitHub não retornou o perfil autorizado.")
        profile = profile_response.json()

    scopes_value = str(token_payload.get("scope") or token_response.headers.get("X-OAuth-Scopes", ""))
    scopes = [item.strip() for item in scopes_value.split(",") if item.strip()]
    await _upsert_connection(
        user_id=int(signed["user_id"]),
        organization_id=str(signed["organization_id"]),
        provider="github",
        label=f"GitHub · {profile.get('login')}",
        external_account_id=str(profile.get("id")),
        external_account_name=str(profile.get("login") or "GitHub"),
        credentials={
            "access_token": access_token,
            "token_type": token_payload.get("token_type"),
        },
        scopes=scopes,
        details={
            "avatarUrl": profile.get("avatar_url"),
            "profileUrl": profile.get("html_url"),
        },
    )
    return RedirectResponse(
        f"{settings.public_app_url.rstrip('/')}/connections?connected=github"
    )


@router.get("/slack/start")
async def start_slack(identity: ArkIdentity = Depends(get_identity)) -> dict[str, str]:
    _require_access(identity)
    if not settings.slack_client_id or not settings.slack_client_secret:
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
