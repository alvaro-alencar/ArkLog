"""
ArkLog - ORM Table Definitions

All tables use SQLAlchemy 2.0 declarative style with type-annotated mapped columns.
All timestamps are UTC. Foreign keys are enforced.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base
from app.utils.datetime_utils import naive_utcnow


class UserRecord(Base):
    """Registered users via GitHub OAuth."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    github_access_token: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    projects: Mapped[list["ProjectRecord"]] = relationship(back_populates="user")


class ProjectRecord(Base):
    """Persisted project state, migrated from YAML to DB."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    report_style: Mapped[str] = mapped_column(String(50), default="misto")
    tech_stack: Mapped[list[str]] = mapped_column(JSON, default=list)
    business_context: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["UserRecord"] = relationship(back_populates="projects")

    destinations: Mapped[list["ReportDestinationRecord"]] = relationship(back_populates="project")
    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="project")
    commits: Mapped[list["CommitRecord"]] = relationship(back_populates="project")


class ReportDestinationRecord(Base):
    """Configuration for report deliveries (frequency, target task, etc.)."""

    __tablename__ = "report_destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    clickup_task_id: Mapped[str] = mapped_column(String(50), nullable=False)
    schedule: Mapped[str] = mapped_column(String(20), nullable=False)  # daily | weekly
    times: Mapped[list[str]] = mapped_column(JSON, default=list)        # list of HH:MM for daily
    day: Mapped[str] = mapped_column(String(20), default="friday")     # for weekly
    time: Mapped[str] = mapped_column(String(10), default="18:00")     # for weekly
    report_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    window_hours: Mapped[int] = mapped_column(Integer, default=-1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["ProjectRecord"] = relationship(back_populates="destinations")


class CommitRecord(Base):
    """Historical record of every commit processed by ArkLog."""

    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    files_changed: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["ProjectRecord"] = relationship(back_populates="commits")

    __table_args__ = (UniqueConstraint("sha", "project_id", name="uix_sha_project"),)


class ReportRecord(Base):
    """Persisted reports — the historical timeline of ArkLog output."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    content: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["ProjectRecord"] = relationship(back_populates="reports")

    publications: Mapped[list["ReportPublicationRecord"]] = relationship(back_populates="report")


class ReportPublicationRecord(Base):
    """Log of report deliveries to external platforms."""

    __tablename__ = "report_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), nullable=False)
    report: Mapped["ReportRecord"] = relationship(back_populates="publications")
