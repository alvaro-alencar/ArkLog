"""Regression tests for ArkLog cost and credential isolation."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.integrations.github.api_client import _headers
from app.models.database import AsyncSessionLocal, init_db
from app.models.tables import (
    ArkLogAccessRecord,
    ProjectRecord,
    ReportUsageRecord,
    UserRecord,
)
from app.security.access import fail_usage, public_access, reserve_report


def test_trial_is_closed_by_default_and_limited_to_one_report() -> None:
    assert settings.arklog_auto_trial is False
    assert settings.arklog_trial_report_limit == 1
    assert settings.ai_trial_max_tokens <= settings.ai_max_tokens
    assert settings.ai_trial_max_prompt_chars < settings.ai_max_prompt_chars


def test_public_access_never_hides_the_real_server_quota() -> None:
    access = ArkLogAccessRecord(
        user_id=1,
        status="TRIAL",
        report_limit=1,
        reports_used=1,
        is_admin=False,
    )
    assert public_access(access)["remainingReports"] == 0


def test_github_reads_never_fall_back_to_an_owner_token() -> None:
    assert "Authorization" not in _headers(token=None, use_global_token=False)
    assert "Authorization" not in _headers(token=None, use_global_token=True)
    assert _headers(token="user-oauth-token")["Authorization"] == "Bearer user-oauth-token"


@pytest.mark.asyncio
async def test_failed_generation_returns_the_trial_slot_exactly_once() -> None:
    await init_db()
    unique = uuid4().hex

    async with AsyncSessionLocal() as session, session.begin():
        user = UserRecord(
            username=f"quota-{unique}@example.com",
            email=f"quota-{unique}@example.com",
            github_access_token="",
            ark_user_id=f"ark-{unique}",
            ark_organization_id=f"org-{unique}",
        )
        session.add(user)
        await session.flush()

        access = ArkLogAccessRecord(
            user_id=user.id,
            status="TRIAL",
            report_limit=1,
            reports_used=0,
            is_admin=False,
        )
        project = ProjectRecord(
            name=f"project-{unique}",
            repo_full_name="octocat/Hello-World",
            user_id=user.id,
        )
        session.add_all([access, project])
        await session.flush()
        user_id = user.id
        project_id = project.id
        access_id = access.id

    identity = SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        access=SimpleNamespace(
            id=access_id,
            status="TRIAL",
            report_limit=1,
            reports_used=0,
        ),
    )
    usage, is_new = await reserve_report(
        identity,
        f"request-{unique}",
        project_id=project_id,
    )
    assert is_new is True

    async with AsyncSessionLocal() as session:
        reserved_access = await session.scalar(
            select(ArkLogAccessRecord).where(ArkLogAccessRecord.id == access_id)
        )
        assert reserved_access is not None
        assert reserved_access.reports_used == 1

    await fail_usage(usage.id, "provider unavailable")
    await fail_usage(usage.id, "duplicate failure callback")

    async with AsyncSessionLocal() as session:
        final_access = await session.scalar(
            select(ArkLogAccessRecord).where(ArkLogAccessRecord.id == access_id)
        )
        final_usage = await session.scalar(
            select(ReportUsageRecord).where(ReportUsageRecord.id == usage.id)
        )
        assert final_access is not None
        assert final_usage is not None
        assert final_access.reports_used == 0
        assert final_usage.status == "FAILED"
