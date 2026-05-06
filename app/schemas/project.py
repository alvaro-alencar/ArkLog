"""ArkLog - Project response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectSummary(BaseModel):
    name: str
    repo_full_name: str
    clickup_task_id: str
    total_reports: int
    total_commits: int
    last_report_at: Optional[datetime]
    last_commit_at: Optional[datetime]


class ProjectListResponse(BaseModel):
    count: int
    projects: list[ProjectSummary]
