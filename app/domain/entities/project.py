"""
ArkLog - Project Entity

Represents a monitored software project. Loaded from projects.yaml and
used to configure the full pipeline: collection → analysis → report → publish.

Each project can have multiple ReportDestinations — different schedules,
ClickUp tasks, and report styles per audience (own workspace vs contractor).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportDestination:
    """A single reporting destination: where, when, and how to report."""

    label: str
    clickup_task_id: str
    schedule: str       # "daily" | "weekly"
    times: tuple[str, ...]  # HH:MM strings — for daily
    day: str            # day-of-week — for weekly (e.g. "friday")
    time: str           # HH:MM — for weekly
    report_style: str   # "misto" | "executivo" | "tecnico"
    window_days: int    # 0=use event commits only; N=fetch last N days from DB


@dataclass(frozen=True)
class Project:
    name: str
    repo_owner: str
    repo_name: str
    description: str = ""
    report_style: str = "misto"
    tech_stack: tuple[str, ...] = field(default_factory=tuple)
    business_context: str = ""
    reports: tuple[ReportDestination, ...] = field(default_factory=tuple)

    @property
    def repo_full_name(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"

    @property
    def formatted_stack(self) -> str:
        return ", ".join(self.tech_stack) if self.tech_stack else "Not specified"

    @property
    def clickup_task_id(self) -> str:
        """First destination's task ID — backward-compat for DB get_or_create."""
        return self.reports[0].clickup_task_id if self.reports else ""

    @property
    def daily_destinations(self) -> list[ReportDestination]:
        return [r for r in self.reports if r.schedule == "daily"]

    @property
    def weekly_destinations(self) -> list[ReportDestination]:
        return [r for r in self.reports if r.schedule == "weekly"]
