"""Shared test fixtures."""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.deps import get_identity
from app.main import app


def _test_identity() -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(
            id=1,
            username="arklog-test",
            email="arklog-test@arksystem.net",
            github_access_token="",
            is_platform_admin=True,
        ),
        access=SimpleNamespace(
            id=1,
            user_id=1,
            status="ACTIVE",
            report_limit=-1,
            reports_used=0,
            is_admin=True,
            approved_at=None,
            blocked_reason=None,
        ),
        ark_session={
            "user": {"id": "test-user", "email": "arklog-test@arksystem.net"},
            "organization": {"id": "test-org", "name": "ArkLog Test", "slug": "test"},
        },
        token="test-ark-session",
    )


@pytest.fixture
async def client():
    async def override_identity() -> SimpleNamespace:
        return _test_identity()

    app.dependency_overrides[get_identity] = override_identity
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_identity, None)


@pytest.fixture
async def unauthenticated_client():
    app.dependency_overrides.pop(get_identity, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
