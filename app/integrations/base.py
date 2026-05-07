"""
ArkLog - Base Publisher Interface

All report destination adapters must implement this interface.
Implementing BasePublisher + registering in _wire_event_handlers() is
the entire contract for adding a new platform.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePublisher(ABC):
    """
    Abstract base for all report publishers.

    A publisher subscribes to `report.generated` and delivers the AI-generated
    report to one external platform (ClickUp, Slack, Notion, etc.).

    Payload keys available in handle_report_generated:
        project_name  str   — human-readable project name
        content       str   — full Markdown report from the AI
        summary       str   — one-line summary (first non-empty line of content)
        commit_count  int   — number of commits in this batch
        trigger       str   — "webhook" | "daily_scheduled" | "weekly_scheduled" | "backfill"
        report_id     int   — DB primary key of the ReportRecord (use for status updates)
        clickup_task_id str — destination task ID (ClickUp-specific; may be absent on others)
    """

    @abstractmethod
    async def handle_report_generated(self, payload: dict[str, Any]) -> None:
        """Receive a report.generated event and publish to the target platform."""

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources (HTTP sessions, connections)."""
