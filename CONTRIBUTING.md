# Contributing to ArkLog

ArkLog welcomes contributions — especially new publisher integrations. Here's everything you need to know.

---

## Setup

```bash
git clone https://github.com/alvaro-alencar/ArkLog.git
cd ArkLog
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
cp projects.yaml.example projects.yaml
alembic upgrade head
```

---

## The highest-impact contribution: a new publisher

ArkLog's event bus makes adding a new destination platform straightforward. The `report.generated` event fires after every report — subscribing to it is all you need.

### 1. Create the adapter

```
app/integrations/<platform>/
├── __init__.py
├── client.py      # HTTP wrapper for the platform API
└── publisher.py   # Subscribes to report.generated
```

### 2. Implement the publisher

```python
# app/integrations/slack/publisher.py
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

class SlackPublisher:
    async def handle_report_generated(self, payload: dict[str, Any]) -> None:
        project = payload.get("project_name", "")
        content = payload.get("content", "")
        webhook_url = payload.get("slack_webhook_url", "")  # from config or payload

        # format and post to Slack
        logger.info("slack_report_posted", project=project)

    async def close(self) -> None:
        pass  # close HTTP session if applicable
```

### 3. Register in events.py

```python
# app/core/events.py — inside _wire_event_handlers()
from app.integrations.slack.publisher import SlackPublisher

slack_pub = SlackPublisher()
event_bus.subscribe("report.generated", slack_pub.handle_report_generated)
```

### 4. Add config fields

```python
# app/core/config.py
slack_webhook_url: str = Field(default="")
```

### 5. Update projects.yaml format (if needed)

If your publisher needs a per-project destination ID (like a channel ID), add it to `ReportDestinationEntry` in `app/config/projects.py`.

---

## Code conventions

- **Type hints everywhere** — no untyped functions
- **Structured logging** — `structlog.get_logger(__name__)`, key-value pairs only
- **No `print()`** — use logger
- **Async all the way** — no blocking I/O in async functions
- **No bare `except`** — catch specific exceptions
- **Naive UTC datetimes** — use `naive_utcnow()` from `app/utils/datetime_utils.py`

## Running tests

```bash
pytest
```

## Submitting a PR

1. Fork the repo
2. Create a branch: `feat/slack-publisher` or `fix/scheduler-grace-time`
3. Keep PRs focused — one feature or fix per PR
4. Include tests for new behavior
5. Update the relevant `README.md` files in the affected directories
