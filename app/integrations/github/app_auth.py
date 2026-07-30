"""GitHub App authentication for user-selected repository installations.

ArkLog never stores a broad personal access token. It stores only the installation ID
selected by the Ark user and mints short-lived installation tokens on demand.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt

from app.core.config import settings


class GitHubAppError(RuntimeError):
    """Safe GitHub App failure that can be surfaced without leaking credentials."""


def _private_key() -> str:
    key = settings.github_app_private_key.strip().replace("\\n", "\n")
    if not key:
        raise GitHubAppError("GitHub App private key is not configured.")
    return key


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": settings.github_api_version,
        "User-Agent": f"ArkLog/{settings.app_version}",
    }


def create_app_jwt(*, now: int | None = None) -> str:
    """Create a short-lived JWT used only to authenticate the ArkLog GitHub App."""
    if not settings.github_app_configured:
        raise GitHubAppError("GitHub App is not configured.")
    issued_at = int(now if now is not None else time.time())
    payload = {
        "iat": issued_at - 60,
        "exp": issued_at + 540,
        "iss": settings.github_client_id,
    }
    encoded = jwt.encode(payload, _private_key(), algorithm="RS256")
    return str(encoded)


async def exchange_user_code(code: str) -> str:
    """Exchange the installation callback code for a temporary user token.

    The token is used only to verify that the signed-in GitHub user can access the
    installation they just selected. It is deliberately never persisted.
    """
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise GitHubAppError("GitHub returned an invalid authorization response.") from exc
    token = str(payload.get("access_token") or "")
    if not response.is_success or not token:
        raise GitHubAppError("GitHub did not complete the installation authorization.")
    return token


async def resolve_user_installation(
    user_token: str,
    requested_installation_id: int | None,
) -> dict[str, Any]:
    """Verify that the temporary GitHub user token can access the installation."""
    app_id = int(settings.github_app_id)
    matches: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=25.0) as client:
        for page in range(1, 11):
            response = await client.get(
                f"{settings.github_api_base_url}/user/installations",
                headers=_headers(user_token),
                params={"per_page": 100, "page": page},
            )
            if response.status_code in {401, 403}:
                raise GitHubAppError("GitHub authorization expired. Start the connection again.")
            if not response.is_success:
                raise GitHubAppError("GitHub could not verify the selected installation.")
            payload = response.json()
            installations = payload.get("installations", [])
            for installation in installations:
                if int(installation.get("app_id") or 0) != app_id:
                    continue
                if requested_installation_id is not None and int(
                    installation.get("id") or 0
                ) != requested_installation_id:
                    continue
                matches.append(installation)
            if len(installations) < 100:
                break

    if requested_installation_id is not None:
        if len(matches) != 1:
            raise GitHubAppError(
                "The selected GitHub installation does not belong to the authorized account."
            )
        return matches[0]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise GitHubAppError("No ArkLog GitHub App installation was found for this account.")
    raise GitHubAppError(
        "GitHub returned multiple installations without identifying the selected one. "
        "Start the connection again from ArkLog."
    )


async def create_installation_token(
    installation_id: int,
    *,
    repository_id: int | None = None,
) -> str:
    """Mint an expiring installation token, optionally restricted to one repository."""
    body: dict[str, Any] = {}
    if repository_id is not None:
        body["repository_ids"] = [repository_id]
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            f"{settings.github_api_base_url}/app/installations/{installation_id}/access_tokens",
            headers=_headers(create_app_jwt()),
            json=body,
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise GitHubAppError("GitHub returned an invalid installation token response.") from exc
    token = str(payload.get("token") or "")
    if not response.is_success or not token:
        raise GitHubAppError(
            "GitHub could not create temporary access for this installation. Reinstall the app."
        )
    return token


async def list_installation_repositories(installation_id: int) -> list[dict[str, Any]]:
    """List only repositories explicitly selected in this GitHub App installation."""
    token = await create_installation_token(installation_id)
    repositories: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=25.0) as client:
        for page in range(1, 11):
            response = await client.get(
                f"{settings.github_api_base_url}/installation/repositories",
                headers=_headers(token),
                params={"per_page": 100, "page": page},
            )
            if response.status_code in {401, 403}:
                raise GitHubAppError("Reconnect the GitHub App to refresh repository access.")
            if not response.is_success:
                raise GitHubAppError("GitHub could not list the selected repositories.")
            payload = response.json()
            items = payload.get("repositories", [])
            repositories.extend(items)
            if len(items) < 100:
                break
    return repositories
