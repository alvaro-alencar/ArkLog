"""ArkLog - Analytics response schemas."""

from typing import Optional

from pydantic import BaseModel


class ProjectStats(BaseModel):
    project_name: str
    total_commits: int
    total_reports: int
    published_reports: int
    avg_commits_per_day: float
    last_activity_days_ago: Optional[int]


class HealthScore(BaseModel):
    project_name: str
    score: int    # 0–100
    grade: str    # A / B / C / D / F
    factors: dict[str, int]  # activity, coverage, recency


class AnalyticsSummaryResponse(BaseModel):
    total_projects: int
    total_commits: int
    total_reports: int
    most_active_project: Optional[str]
    projects: list[ProjectStats]
