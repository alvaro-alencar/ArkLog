"""
ArkLog - Projects Configuration Loader

Loads and validates project definitions from projects.yaml.
Projects are the core configuration unit of ArkLog — each maps a GitHub
repository to a ClickUp task with reporting preferences and schedule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.domain.entities.project import Project

logger = structlog.get_logger(__name__)


class ProjectYamlEntry(BaseModel):
    """Validates a single project entry from YAML before converting to domain entity."""

    name: str
    repo_owner: str
    repo_name: str
    clickup_task_id: str
    description: str = ""
    report_style: str = Field(default="misto", pattern="^(executivo|tecnico|misto)$")
    tech_stack: list[str] = Field(default_factory=list)
    business_context: str = ""
    schedule: list[str] = Field(default_factory=list)

    @field_validator("schedule")
    @classmethod
    def validate_schedule_format(cls, v: list[str]) -> list[str]:
        for time_str in v:
            parts = time_str.split(":")
            if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                raise ValueError(f"Invalid schedule time '{time_str}'. Use HH:MM format.")
        return v

    def to_entity(self) -> Project:
        return Project(
            name=self.name,
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            clickup_task_id=self.clickup_task_id,
            description=self.description,
            report_style=self.report_style,
            tech_stack=tuple(self.tech_stack),
            business_context=self.business_context,
            schedule=tuple(self.schedule),
        )


class ProjectsConfig:
    """
    Loads and caches project configurations from YAML.

    The file is read once and cached. To reload, restart the application.
    Falls back to empty list if the file doesn't exist (useful in CI/CD).
    """

    def __init__(self) -> None:
        self._projects: Optional[list[Project]] = None

    @property
    def projects(self) -> list[Project]:
        if self._projects is None:
            self._projects = self._load()
        return self._projects

    def get_by_repo(self, repo_full_name: str) -> Optional[Project]:
        """Find a project by its GitHub repo (owner/repo)."""
        return next((p for p in self.projects if p.repo_full_name == repo_full_name), None)

    def get_by_name(self, name: str) -> Optional[Project]:
        return next((p for p in self.projects if p.name == name), None)

    def _load(self) -> list[Project]:
        config_path = Path(settings.projects_config_path)

        if not config_path.exists():
            logger.warning(
                "projects_config_not_found",
                path=str(config_path),
                hint="Copy projects.yaml.example to projects.yaml and configure your projects.",
            )
            return []

        with config_path.open() as f:
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
