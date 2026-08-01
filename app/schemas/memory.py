"""Schemas for human review and Ark Memory Protocol events."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ReviewVerdict = Literal["approved", "edited", "rejected"]


class ReportReviewRequest(BaseModel):
    verdict: ReviewVerdict
    approved_content: str | None = None
    reason: str = Field(default="", max_length=4000)
    labels: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_approved_content(self) -> "ReportReviewRequest":
        if self.verdict == "edited" and not (self.approved_content or "").strip():
            raise ValueError("approved_content is required when verdict is edited")
        if self.verdict == "approved" and self.approved_content is not None:
            raise ValueError("approved_content must be omitted when verdict is approved")
        return self


class ReportReviewResponse(BaseModel):
    protocol: Literal["ark.memory.v1"] = "ark.memory.v1"
    event_id: str
    event_type: Literal["report.reviewed"] = "report.reviewed"
    occurred_at: datetime
    report_id: int
    verdict: ReviewVerdict
    original_content: str
    approved_content: str | None
    reason: str
    labels: list[str]


class MemoryRule(BaseModel):
    key: str
    statement: str
    evidence_count: int
    last_seen_at: datetime


class MemoryProfileResponse(BaseModel):
    protocol: Literal["ark.memory.v1"] = "ark.memory.v1"
    user_id: int
    review_count: int
    approved_count: int
    edited_count: int
    rejected_count: int
    rules: list[MemoryRule]
    examples: list[ReportReviewResponse]
