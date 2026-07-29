"""Tests for trusted report scheduler job registration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schedulers.report_scheduler import register_project_schedules


class FakeSession:
    def __init__(self, access: object | None) -> None:
        self.access = access

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def scalar(self, _statement: object) -> object | None:
        return self.access


class FakeSessionFactory:
    def __init__(self, access: object | None) -> None:
        self.access = access

    def __call__(self) -> FakeSession:
        return FakeSession(self.access)


def daily_destination(destination_id: int, *times: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=destination_id,
        schedule="daily",
        times=list(times),
        day="friday",
        time="18:00",
    )


def weekly_destination(destination_id: int, day: str, time: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=destination_id,
        schedule="weekly",
        times=[],
        day=day,
        time=time,
    )


def project_repository(projects: list[SimpleNamespace]) -> MagicMock:
    repository = MagicMock()
    repository.get_all_active = AsyncMock(return_value=projects)
    return repository


@pytest.mark.asyncio
async def test_registers_only_trusted_admin_schedules() -> None:
    project = SimpleNamespace(
        id=7,
        user_id=11,
        destinations=[
            daily_destination(21, "09:00", "18:00"),
            weekly_destination(22, "friday", "17:30"),
        ],
    )
    scheduler = MagicMock()
    repository = project_repository([project])

    with (
        patch(
            "app.schedulers.report_scheduler.AsyncSessionLocal",
            FakeSessionFactory(SimpleNamespace(status="ACTIVE", is_admin=True)),
        ),
        patch("app.schedulers.report_scheduler.ProjectRepository", return_value=repository),
        patch("app.schedulers.report_scheduler.scheduler", scheduler),
    ):
        await register_project_schedules()

    assert scheduler.add_job.call_count == 3
    calls = scheduler.add_job.call_args_list
    assert all(call.kwargs["trigger"] == "cron" for call in calls)
    assert calls[0].kwargs["args"] == [7, 21, "daily_scheduled"]
    assert calls[2].kwargs["args"] == [7, 22, "weekly_scheduled"]
    assert calls[2].kwargs["day_of_week"] == "fri"


@pytest.mark.asyncio
async def test_does_not_register_jobs_without_authorized_admin_access() -> None:
    project = SimpleNamespace(
        id=7,
        user_id=11,
        destinations=[daily_destination(21, "09:00")],
    )
    scheduler = MagicMock()
    repository = project_repository([project])

    with (
        patch("app.schedulers.report_scheduler.AsyncSessionLocal", FakeSessionFactory(None)),
        patch("app.schedulers.report_scheduler.ProjectRepository", return_value=repository),
        patch("app.schedulers.report_scheduler.scheduler", scheduler),
    ):
        await register_project_schedules()

    scheduler.add_job.assert_not_called()


@pytest.mark.asyncio
async def test_no_projects_creates_no_jobs() -> None:
    scheduler = MagicMock()
    repository = project_repository([])

    with (
        patch("app.schedulers.report_scheduler.AsyncSessionLocal", FakeSessionFactory(None)),
        patch("app.schedulers.report_scheduler.ProjectRepository", return_value=repository),
        patch("app.schedulers.report_scheduler.scheduler", scheduler),
    ):
        await register_project_schedules()

    scheduler.add_job.assert_not_called()
