"""Persistence models for Ark Memory Protocol v1."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base
from app.utils.datetime_utils import naive_utcnow


class ReportReviewRecord(Base):
    """Human judgment over a generated report.

    Reviews are append-only protocol events. A report may have several revisions,
    but an event id is globally unique so clients can retry safely.
    """

    __tablename__ = "report_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    protocol: Mapped[str] = mapped_column(String(32), default="ark.memory.v1", nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), default="report.reviewed", nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    approved_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow, nullable=False)

    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("report_id", "event_id", name="uix_report_review_event"),
    )
