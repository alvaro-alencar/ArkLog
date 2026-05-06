"""
ArkLog - ClickUp API Client

Async HTTP wrapper around ClickUp API v2.
Authentication via Authorization header (personal API token).

Rate limit: ClickUp free plan allows ~100 req/min.
This client lets httpx handle connection pooling and timeouts.
"""

import httpx
import structlog

from app.core.config import settings
from app.utils.clickup_formatter import markdown_to_clickup

logger = structlog.get_logger(__name__)


class ClickUpClient:
    """Thin async HTTP client for ClickUp API v2."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.clickup_base_url,
            headers={
                "Authorization": settings.clickup_api_token,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def post_task_comment(self, task_id: str, text: str) -> str:
        """
        Post a comment to a ClickUp task.
        Returns the comment ID on success.
        Raises httpx.HTTPStatusError on non-2xx responses.
        """
        response = await self._http.post(
            f"/task/{task_id}/comment",
            json={"comment_text": markdown_to_clickup(text), "notify_all": False},
        )
        response.raise_for_status()
        comment_id = str(response.json().get("id", ""))
        logger.info("clickup_comment_posted", task_id=task_id, comment_id=comment_id)
        return comment_id

    async def close(self) -> None:
        await self._http.aclose()
