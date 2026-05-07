"""ArkLog - Project schemas for API requests and responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReportDestinationSchema(BaseModel):
    label: str
    clickup_task_id: str
    schedule: Literal["daily", "weekly"]
    times: list[str] = Field(default_factory=list)
    day: str = "friday"
    time: str = "18:00"
    report_style: Optional[str] = None
    window_hours: int = -1


class InstantReportRequest(BaseModel):
    window_hours: int = -1
    destination_id: Optional[int] = None


class ProjectCreate(BaseModel):
    name: str
    repo_full_name: str
    description: str = ""
    report_style: str = "misto"
    tech_stack: list[str] = Field(default_factory=list)
    business_context: str = ""
    reports: list[ReportDestinationSchema] = Field(default_factory=list)


class ReportDestinationResponse(ReportDestinationSchema):
    id: int

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: int
    name: str
    repo_full_name: str
    description: str
    report_style: str
    tech_stack: list[str]
    business_context: str
    created_at: datetime
    destinations: list[ReportDestinationResponse]

    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    id: int
    name: str
    repo_full_name: str
    description: str
    created_at: datetime


class ProjectListResponse(BaseModel):
    count: int
    projects: list[ProjectSummary]
