# app/domain — Domain Entities

Pure Python dataclasses with zero framework dependencies. These are the canonical data structures of ArkLog — they can be used, tested, and reasoned about without importing FastAPI, SQLAlchemy, or anything else.

## entities/

### `commit.py`
`Commit` — immutable representation of a single git commit. Created by `CommitParser` from webhook payloads or by the GitHub API client during backfill. Contains derived properties (`short_sha`, `subject`, `affected_directories`, `affected_extensions`) computed from raw data.

`CommitFile` — a single file changed within a commit. Provides `extension` and `directory` properties for aggregation.

### `project.py`
`Project` — configuration entity loaded from `projects.yaml`. Frozen dataclass (immutable after load). Contains the full list of `ReportDestination` objects.

`ReportDestination` — a single reporting target: which ClickUp task, what schedule (daily/weekly), what report style, and how many days of commits to fetch from the DB. The `daily_destinations` and `weekly_destinations` properties on `Project` filter by schedule type.

### `report.py`
`ReportStatus` and `ReportTrigger` enums defining valid states and trigger types for `ReportRecord`.

## events/

Reserved for typed event payloads. Currently ArkLog uses plain `dict[str, Any]` for event payloads for simplicity — this directory is the migration target when payload typing becomes a priority.
