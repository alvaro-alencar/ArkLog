"""
ArkLog - OpenAI Client

Async OpenAI client configured from settings. Compatible with OpenRouter
or any OpenAI-compatible endpoint by changing OPENAI_BASE_URL.

Singleton pattern — one client per process, lazy-initialized on first use.
"""

from openai import AsyncOpenAI

from app.core.config import settings

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Return the shared async OpenAI client, creating it if necessary."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return _client
