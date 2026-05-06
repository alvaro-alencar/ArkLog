"""
ArkLog - Domain Event Types

Centralized catalog of all events that flow through the EventBus.
To trace data flow, follow publish() and subscribe() calls using these types.

Event flow:
  github.push → commit.batch_ready → report.requested → report.generated → report.published
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.utils.datetime_utils import naive_utcnow


class EventType(str, Enum):
    # GitHub
    GITHUB_PUSH = "github.push"
    GITHUB_PING = "github.ping"

    # Commit analysis
    COMMIT_ANALYZED = "commit.analyzed"
    COMMIT_BATCH_READY = "commit.batch_ready"

    # Report lifecycle
    REPORT_REQUESTED = "report.requested"
    REPORT_GENERATED = "report.generated"
    REPORT_FAILED = "report.failed"

    # Publication
    REPORT_PUBLISHED = "report.published"
    REPORT_PUBLISH_FAILED = "report.publish_failed"

    # Scheduler
    SCHEDULE_TRIGGERED = "schedule.triggered"


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_type: EventType
    occurred_at: datetime = field(default_factory=naive_utcnow)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "payload": self.payload,
        }
