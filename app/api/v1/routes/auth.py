"""
ArkLog - GitHub OAuth Authentication

Handles the OAuth2 flow with GitHub:
1. Redirect to GitHub login
2. Callback with 'code'
3. Exchange code for Access Token
4. Fetch User Profile
5. Create/Update UserRecord & Issue JWT
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
import structlog
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.models.tables import UserRecord

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/login/github")
async def login_github() -> RedirectResponse:
    """Redirect user to GitHub OAuth authorize page."""
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured (missing CLIENT_ID)"
        )

    scope = "read:user user:email repo"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_redirect_uri}"
        f"&scope={scope}"
    )
    return RedirectResponse(url)


@router.get("/callback/github")
async def github_callback(code: str = Query(...)) -> dict[str, Any]:
    """Exchange code for token and return JWT to the frontend."""
    logger.info("github_callback_received", code=code[:5] + "...")
    # 1. Exchange code for access token
    async with httpx.AsyncClient() as client:
        logger.debug("github_exchanging_code")
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            params={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            logger.error("github_oauth_error", data=token_data)
            raise HTTPException(status_code=400, detail="Failed to retrieve access token from GitHub")

        # 2. Fetch User Profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"},
        )
        user_resp.raise_for_status()
        user_profile = user_resp.json()

        # 3. Fetch Primary Email
        email_resp = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"token {access_token}"},
        )
        email_resp.raise_for_status()
        emails = email_resp.json()
        primary_email = next((e["email"] for e in emails if e["primary"]), None)

    # 4. Upsert User in DB
    github_id = user_profile["id"]
    username = user_profile["login"]
    avatar_url = user_profile.get("avatar_url")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(UserRecord).where(UserRecord.github_id == github_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.username = username
                user.email = primary_email
                user.avatar_url = avatar_url
                user.github_access_token = access_token
            else:
                user = UserRecord(
                    github_id=github_id,
                    username=username,
                    email=primary_email,
                    avatar_url=avatar_url,
                    github_access_token=access_token,
                )
                session.add(user)
            
            await session.flush()
            user_id = user.id

    # 5. Issue JWT
    token = _create_jwt({"sub": str(user_id), "username": username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": username,
            "avatar_url": avatar_url,
        }
    }


def _create_jwt(data: dict) -> str:
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
