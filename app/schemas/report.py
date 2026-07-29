"""ArkLog - Report response schemas."""

from datetime import datetime

from pydantic import BaseModel


class ReportSummaryResponse(BaseModel):
    id: int
    project_id: int
    project_name: str
    trigger: str
    status: str
    summary: str
    commit_count: int
    generated_at: datetime

    class Config:
        from_attributes = True


class ReportDetailResponse(ReportSummaryResponse):
    content: str


class ReportListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    reports: list[ReportSummaryResponse]
