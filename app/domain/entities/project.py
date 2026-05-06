"""
ArkLog - Project Entity

Represents a monitored software project. Loaded from projects.yaml and
used to configure the full pipeline: collection → analysis → report → publish.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Project:
    """
    Configuration entity for a monitored project.

    Each project maps a GitHub repository to a ClickUp task and defines
    how reports should be generated (style, schedule, context).
    """

    name: str
    repo_owner: str
    repo_name: str
    clickup_task_id: str
    description: str = ""
    report_style: str = "misto"  # executivo | tecnico | misto
    tech_stack: tuple[str, ...] = field(default_factory=tuple)
    business_context: str = ""
    schedule: tuple[str, ...] = field(default_factory=tuple)  # HH:MM strings

    @property
    def repo_full_name(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"

    @property
    def formatted_stack(self) -> str:
        return ", ".join(self.tech_stack) if self.tech_stack else "Not specified"
