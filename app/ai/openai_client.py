"""
ArkLog - AI Client

Async OpenAI-compatible client configured from settings.
Works with OpenRouter, OpenAI, or any OpenAI-format endpoint
by changing AI_BASE_URL and AI_API_KEY.

Singleton pattern — one client per process, lazy-initialized on first use.
"""

from openai import AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Return the shared async AI client, creating it if necessary."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/arklog",
                "X-Title": "ArkLog",
            },
        )
    return _client
