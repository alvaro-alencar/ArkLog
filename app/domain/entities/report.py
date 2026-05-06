"""
ArkLog - Report Entity

The central output artifact of ArkLog. Carries the AI-generated content,
metadata about what triggered it, and its publication state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ReportStatus(str, Enum):
    PENDING = "pending"
    GENERATED = "generated"
    PUBLISHED = "published"
    FAILED = "failed"


class ReportTrigger(str, Enum):
    WEBHOOK = "webhook"      # Triggered by a GitHub push event
    SCHEDULED = "scheduled"  # Triggered by the scheduler (even without commits)
    MANUAL = "manual"        # Triggered via API call


@dataclass
class Report:
    """
    A generated progress report for a project.

    State machine: PENDING → GENERATED → PUBLISHED
                           ↘ FAILED
    """

    project_name: str
    trigger: ReportTrigger
    generated_at: datetime = field(default_factory=datetime.utcnow)
    status: ReportStatus = ReportStatus.PENDING

    content: str = ""   # Full AI-generated report
    summary: str = ""   # Short executive summary (first paragraph)

    commit_count: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    clickup_comment_id: Optional[str] = None
    published_at: Optional[datetime] = None

    def mark_generated(self, content: str, summary: str) -> None:
        self.content = content
        self.summary = summary
        self.status = ReportStatus.GENERATED

    def mark_published(self, clickup_comment_id: str) -> None:
        self.clickup_comment_id = clickup_comment_id
        self.published_at = datetime.utcnow()
        self.status = ReportStatus.PUBLISHED

    def mark_failed(self) -> None:
        self.status = ReportStatus.FAILED
