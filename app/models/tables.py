"""
ArkLog - ORM Table Definitions

All tables use SQLAlchemy 2.0 declarative style with type-annotated mapped columns.
All timestamps are UTC. Foreign keys are enforced.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base
from app.utils.datetime_utils import naive_utcnow


class ProjectRecord(Base):
    """Persisted project state, synced from projects.yaml on startup."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    clickup_task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="project")
    commits: Mapped[list["CommitRecord"]] = relationship(back_populates="project")


class CommitRecord(Base):
    """Historical record of every commit processed by ArkLog."""

    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    files_changed: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=naive_utcnow)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["ProjectRecord"] = relationship(back_populates="commits")


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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    clickup_comment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project: Mapped["ProjectRecord"] = relationship(back_populates="reports")
