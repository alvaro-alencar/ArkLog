"""ArkLog - Report response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportSummaryResponse(BaseModel):
    id: int
    project_name: str
    trigger: str
    status: str
    summary: str
    commit_count: int
    generated_at: datetime
    published_at: Optional[datetime]
    clickup_comment_id: Optional[str]


class ReportDetailResponse(ReportSummaryResponse):
    content: str


class ReportListResponse(BaseModel):
    project_name: str
    total: int
    limit: int
    offset: int
    reports: list[ReportSummaryResponse]
