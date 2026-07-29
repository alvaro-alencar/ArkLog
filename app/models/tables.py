"""ArkLog ORM table definitions."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base
from app.utils.datetime_utils import naive_utcnow


class UserRecord(Base):
    """Local projection of an authenticated Ark account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    github_access_token: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    ark_user_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    ark_organization_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), default="America/Sao_Paulo", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="pt-BR", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    projects: Mapped[list["ProjectRecord"]] = relationship(back_populates="user")
    integrations: Mapped[list["UserIntegrationRecord"]] = relationship(back_populates="user")
    arklog_access: Mapped[Optional["ArkLogAccessRecord"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    report_usages: Mapped[list["ReportUsageRecord"]] = relationship(back_populates="user")


class ArkLogAccessRecord(Base):
    """Product authorization and server-enforced report quota."""

    __tablename__ = "arklog_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    report_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reports_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=naive_utcnow, onupdate=naive_utcnow
    )

    user: Mapped["UserRecord"] = relationship(back_populates="arklog_access")


class UserIntegrationRecord(Base):
    """Per-user integration credentials."""

    __tablename__ = "user_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False)
    credentials: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    user: Mapped["UserRecord"] = relationship(back_populates="integrations")

    __table_args__ = (
        UniqueConstraint("user_id", "integration_type", name="uix_user_integration"),
    )


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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
    usages: Mapped[list["ReportUsageRecord"]] = relationship(back_populates="project")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uix_project_user_name"),
    )


class ReportDestinationRecord(Base):
    __tablename__ = "report_destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    clickup_task_id: Mapped[str] = mapped_column(String(50), nullable=False)
    schedule: Mapped[str] = mapped_column(String(20), nullable=False)
    times: Mapped[list[str]] = mapped_column(JSON, default=list)
    day: Mapped[str] = mapped_column(String(20), default="friday")
    time: Mapped[str] = mapped_column(String(10), default="18:00")
    report_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    window_hours: Mapped[int] = mapped_column(Integer, default=-1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["ProjectRecord"] = relationship(back_populates="destinations")


class CommitRecord(Base):
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
    usages: Mapped[list["ReportUsageRecord"]] = relationship(back_populates="report")


class ReportUsageRecord(Base):
    """Idempotency ledger and cost-control audit for every requested report."""

    __tablename__ = "report_usages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger: Mapped[str] = mapped_column(String(50), default="instant", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="RESERVED", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    report_id: Mapped[Optional[int]] = mapped_column(ForeignKey("reports.id"), nullable=True)

    user: Mapped["UserRecord"] = relationship(back_populates="report_usages")
    project: Mapped["ProjectRecord"] = relationship(back_populates="usages")
    report: Mapped[Optional["ReportRecord"]] = relationship(back_populates="usages")

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uix_report_usage_idempotency"),
    )


class ReportPublicationRecord(Base):
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
