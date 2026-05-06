"""Tests for the report scheduler job registration."""

from unittest.mock import MagicMock, patch

from app.domain.entities.project import Project
from app.schedulers.report_scheduler import register_project_schedules


SAMPLE_PROJECTS = [
    Project(
        name="SmartEAD",
        repo_owner="my-org",
        repo_name="smartead",
        clickup_task_id="abc123",
        schedule=("09:00", "18:00"),
    ),
    Project(
        name="NexusAI",
        repo_owner="my-org",
        repo_name="nexus-ai",
        clickup_task_id="def456",
        schedule=("12:00",),
    ),
]


def test_register_creates_correct_job_count():
    mock_scheduler = MagicMock()
    with (
        patch("app.schedulers.report_scheduler.scheduler", mock_scheduler),
        patch("app.schedulers.report_scheduler.projects_config") as mock_config,
    ):
        mock_config.projects = SAMPLE_PROJECTS
        register_project_schedules()

    # SmartEAD: 2 jobs, NexusAI: 1 job = 3 total
    assert mock_scheduler.add_job.call_count == 3


def test_register_uses_cron_trigger():
    mock_scheduler = MagicMock()
    with (
        patch("app.schedulers.report_scheduler.scheduler", mock_scheduler),
        patch("app.schedulers.report_scheduler.projects_config") as mock_config,
    ):
        mock_config.projects = SAMPLE_PROJECTS
        register_project_schedules()

    for call in mock_scheduler.add_job.call_args_list:
        assert call.kwargs["trigger"] == "cron"


def test_register_no_projects_creates_no_jobs():
    mock_scheduler = MagicMock()
    with (
        patch("app.schedulers.report_scheduler.scheduler", mock_scheduler),
        patch("app.schedulers.report_scheduler.projects_config") as mock_config,
    ):
        mock_config.projects = []
        register_project_schedules()

    mock_scheduler.add_job.assert_not_called()
