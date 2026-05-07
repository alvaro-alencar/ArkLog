# app/core — Application Infrastructure

The foundational layer. Everything here is framework-level — no business logic.

## Files

### `config.py`
Centralized settings via `pydantic-settings`. All values are read from `.env` (or environment variables). Import `settings` anywhere in the app — never read `os.environ` directly.

Key setting groups:
- `AI_*` — model provider, max tokens per trigger type, temperature
- `GITHUB_*` — webhook secret, personal access token
- `CLICKUP_*` — API token, team ID
- `SCHEDULER_ENABLED` — set to `false` on replica containers to prevent duplicate scheduled jobs

### `events.py`
Two responsibilities in one file:

**1. Application lifecycle** (`on_startup` / `on_shutdown`): initializes the DB, loads projects from YAML, wires all event subscribers, starts the scheduler.

**2. EventBus**: async in-process pub/sub implementing the Observer pattern. All cross-module communication goes through here — Commit Service, Report Service, and Publisher never import each other directly.

```
github.push        → CommitService.handle_push_event
commit.batch_ready → ReportService.handle_commit_batch
report.generated   → ClickUpPublisher.handle_report_generated
```

The EventBus uses `asyncio.gather` for concurrent handler execution. Exceptions in one handler do not affect others — they are logged and swallowed.

### `logging.py`
Configures `structlog` for JSON output in production and human-readable colored output in development. All log entries are structured key-value pairs — never use `print()` or `logging.info("string")` directly.
