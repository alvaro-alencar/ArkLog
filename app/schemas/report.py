"""ArkLog report response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportPublicationResponse(BaseModel):
    platform: str
    target_id: str
    external_id: str | None = None
    status: str
    error_message: str | None = None
    published_at: datetime | None = None


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None = None
    flow_id: int | None = None
    project_name: str
    owner_kind: str
    source_provider: str | None = None
    destination_provider: str | None = None
    trigger: str
    status: str
    summary: str
    item_count: int
    commit_count: int
    generated_at: datetime


class ReportDetailResponse(ReportSummaryResponse):
    content: str
    publications: list[ReportPublicationResponse]


class ReportListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    reports: list[ReportSummaryResponse]
