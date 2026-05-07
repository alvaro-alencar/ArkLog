# app/models — ORM Table Definitions

SQLAlchemy 2.0 declarative models. All timestamps are naive UTC (timezone-unaware) for SQLite compatibility — use `naive_utcnow()` from `app/utils/datetime_utils.py`, never `datetime.utcnow()` (deprecated) or `datetime.now(timezone.utc)` directly.

## Files

### `database.py`
- `AsyncSessionLocal` — session factory for all DB operations
- `init_db()` — creates tables on startup (development only; production uses Alembic)
- `get_session()` — FastAPI dependency for request-scoped sessions

### `tables.py`
Three tables:

**`ProjectRecord`** — one row per configured project. Synced from `projects.yaml` on each push event via `get_or_create`. The `clickup_task_id` field stores the first destination's ID for reference; actual routing uses the event payload.

**`CommitRecord`** — one row per processed commit. `sha` is unique — duplicate webhook deliveries are idempotent. `files_changed` is an integer count (file-level detail is not persisted).

**`ReportRecord`** — one row per generated report. Key fields:
- `trigger` — `webhook | daily_scheduled | weekly_scheduled | backfill`
- `status` — `generated | published`
- `clickup_comment_id` — populated after successful ClickUp post
- `commit_count` — number of commits analyzed (0 for status-inference reports)
