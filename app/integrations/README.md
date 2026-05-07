# app/integrations — External Platform Adapters

Each subdirectory is a self-contained adapter for one external platform. ArkLog's event bus decouples the report generation pipeline from any specific destination — adding a new platform means adding a new adapter here, with zero changes to the core.

## Structure

```
integrations/
├── base.py          # BasePublisher ABC — implement this to add any new destination
├── github/          # Source: reads commits via webhook and REST API
│   ├── api_client.py        # GitHub REST API — fetches commit history (backfill)
│   ├── commit_parser.py     # Parses raw webhook push payload into Commit entities
│   └── webhook_validator.py # HMAC-SHA256 signature verification
│
└── clickup/         # Destination: posts reports as task comments
    ├── client.py            # Async HTTP wrapper for ClickUp API v2
    └── publisher.py         # Implements BasePublisher; subscribes to report.generated
```

---

## Adding a New Publisher (e.g. Slack, Notion, Linear)

1. Create a new directory: `app/integrations/<platform>/`
2. Extend `BasePublisher`:

```python
# app/integrations/slack/publisher.py
from typing import Any
import structlog
from app.integrations.base import BasePublisher

logger = structlog.get_logger(__name__)

class SlackPublisher(BasePublisher):
    async def handle_report_generated(self, payload: dict[str, Any]) -> None:
        project = payload.get("project_name", "")
        content = payload.get("content", "")
        # format and post to Slack
        logger.info("slack_report_posted", project=project)

    async def close(self) -> None:
        pass  # close HTTP session if applicable
```

3. Register it in `app/core/events.py` inside `_wire_event_handlers()`:

```python
from app.integrations.slack.publisher import SlackPublisher

slack_pub = SlackPublisher()
_publishers.append(slack_pub)
event_bus.subscribe("report.generated", slack_pub.handle_report_generated)
```

4. Add any required config fields to `app/core/config.py` and `.env.example`.

> **Payload reference** — `report.generated` provides: `project_name`, `content` (Markdown), `summary`, `commit_count`, `trigger` (`webhook` | `daily_scheduled` | `weekly_scheduled` | `backfill`), `report_id`, `clickup_task_id`. Your publisher reads what it needs and ignores the rest.

---

## GitHub Adapter

### `github/webhook_validator.py`
FastAPI dependency that validates the `X-Hub-Signature-256` header on every incoming webhook request. Rejects requests with invalid HMAC signatures with HTTP 401. Uses `hmac.compare_digest` for timing-safe comparison.

### `github/commit_parser.py`
Converts the raw GitHub push event JSON into a list of typed `Commit` entities. Handles timestamp normalization (GitHub sends ISO 8601 with timezone; we store naive UTC for SQLite compatibility).

### `github/api_client.py`
Paginated GitHub REST API client for fetching the full commit history of a repository. Used exclusively by the backfill endpoint. Requires `GITHUB_TOKEN` for private repositories.

---

## ClickUp Adapter

### `clickup/client.py`
Thin async wrapper around the ClickUp API v2. Converts Markdown report content to visually structured plain text (ClickUp task comment API does not support rich text via the public API). Uses `CLICKUP_API_TOKEN` for authentication — a single personal token works across all workspaces the user is a member of.

### `clickup/publisher.py`
Subscribes to `report.generated`. Adds a metadata header (project name, timestamp in Brasília time, trigger label) and posts the formatted report as a task comment. After posting, updates the `ReportRecord` in the DB with the ClickUp comment ID and `published` status.
