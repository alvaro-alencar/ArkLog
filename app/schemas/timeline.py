"""ArkLog - Timeline response schemas."""

from typing import Optional

from pydantic import BaseModel


class TimelineEntry(BaseModel):
    date: str          # ISO date: YYYY-MM-DD
    commits: int
    reports: int
    summary: Optional[str]  # Latest report summary for that day, if any


class TimelineResponse(BaseModel):
    project_name: str
    period_days: int
    total_commits: int
    total_reports: int
    entries: list[TimelineEntry]
