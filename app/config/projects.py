"""
ArkLog - Projects Configuration Loader

Loads and validates project definitions from projects.yaml.
Each project maps a GitHub repository to one or more ReportDestinations,
each with its own ClickUp task, schedule, report style, and commit window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.domain.entities.project import Project, ReportDestination

logger = structlog.get_logger(__name__)

_VALID_DAYS = frozenset(
    ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
)
_VALID_STYLES = frozenset(["executivo", "tecnico", "misto"])


def _validate_hhmm(value: str) -> None:
    parts = value.split(":")
    try:
        if len(parts) != 2:
            raise ValueError()
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
    except (ValueError, IndexError):
        raise ValueError(f"Invalid time '{value}'. Use HH:MM format (e.g. '09:00').")


class ReportDestinationEntry(BaseModel):
    label: str
    clickup_task_id: str
    schedule: Literal["daily", "weekly"]
    times: list[str] = Field(default_factory=list)   # for daily
    day: str = "friday"                               # for weekly
    time: str = "09:00"                               # for weekly
    report_style: Optional[str] = None               # inherits project default if omitted
    window_days: int = -1                             # -1 = auto (0 for daily, 7 for weekly)

    @field_validator("times")
    @classmethod
    def validate_times(cls, v: list[str]) -> list[str]:
        for t in v:
            _validate_hhmm(t)
        return v

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        if v.lower() not in _VALID_DAYS:
            raise ValueError(f"Invalid day '{v}'. Use monday–sunday.")
        return v.lower()

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        _validate_hhmm(v)
        return v

    @field_validator("report_style")
    @classmethod
    def validate_style(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_STYLES:
            raise ValueError(f"report_style must be one of {sorted(_VALID_STYLES)}")
        return v

    def to_entity(self, project_style: str) -> ReportDestination:
        style = self.report_style or project_style
        if self.window_days == -1:
            window = 0 if self.schedule == "daily" else 7
        else:
            window = self.window_days
        return ReportDestination(
            label=self.label,
            clickup_task_id=self.clickup_task_id,
            schedule=self.schedule,
            times=tuple(self.times),
            day=self.day,
            time=self.time,
            report_style=style,
            window_days=window,
        )


class ProjectYamlEntry(BaseModel):
    name: str
    repo_owner: str
    repo_name: str
    description: str = ""
    report_style: str = Field(default="misto", pattern="^(executivo|tecnico|misto)$")
    tech_stack: list[str] = Field(default_factory=list)
    business_context: str = ""
    reports: list[ReportDestinationEntry] = Field(default_factory=list)

    def to_entity(self) -> Project:
        return Project(
            name=self.name,
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            description=self.description,
            report_style=self.report_style,
            tech_stack=tuple(self.tech_stack),
            business_context=self.business_context,
            reports=tuple(d.to_entity(self.report_style) for d in self.reports),
        )


class ProjectsConfig:
    """Loads and caches project configurations from YAML (read once on startup)."""

    def __init__(self) -> None:
        self._projects: Optional[list[Project]] = None

    @property
    def projects(self) -> list[Project]:
        if self._projects is None:
            self._projects = self._load()
        return self._projects

    def get_by_repo(self, repo_full_name: str) -> Optional[Project]:
        return next((p for p in self.projects if p.repo_full_name == repo_full_name), None)

    def get_by_name(self, name: str) -> Optional[Project]:
        return next((p for p in self.projects if p.name == name), None)

    def _load(self) -> list[Project]:
        config_path = Path(settings.projects_config_path)

        if not config_path.exists():
            logger.warning("projects_config_not_found", path=str(config_path))
            return []

        with config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw or "projects" not in raw:
            return []

        projects: list[Project] = []
        for entry in raw["projects"]:
            try:
                projects.append(ProjectYamlEntry(**entry).to_entity())
            except Exception as exc:
                logger.error("project_entry_invalid", name=entry.get("name", "?"), error=str(exc))

        return projects


projects_config = ProjectsConfig()
