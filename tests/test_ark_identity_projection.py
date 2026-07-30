"""Regression tests for projecting shared Ark identities into ArkLog."""

from uuid import uuid4

import pytest

from app.models.database import AsyncSessionLocal, init_db
from app.models.tables import UserRecord
from app.security import ark_auth


@pytest.mark.asyncio
async def test_ark_identity_never_uses_the_legacy_github_id_column(monkeypatch) -> None:
    unique = uuid4().hex
    ark_user_id = f"ark-user-{unique}"
    organization_id = f"ark-org-{unique}"
    email = f"ark-{unique}@example.com"

    async def fake_introspection(_token: str) -> dict:
        return {
            "user": {
                "id": ark_user_id,
                "email": email,
                "name": "Ark Identity Test",
                "isPlatformAdmin": True,
            },
            "organization": {
                "id": organization_id,
                "name": "Ark Identity Test",
                "slug": f"ark-{unique[:8]}",
            },
        }

    monkeypatch.setattr(ark_auth, "introspect_ark_session", fake_introspection)
    await init_db()

    identity = await ark_auth.resolve_identity("test-session")

    assert identity.user.ark_user_id == ark_user_id
    assert identity.user.github_id is None
    assert identity.access.status == "ACTIVE"
    assert identity.access.is_admin is True

    async with AsyncSessionLocal() as session:
        stored = await session.get(UserRecord, identity.user.id)
        assert stored is not None
        assert stored.ark_user_id == ark_user_id
        assert stored.github_id is None
