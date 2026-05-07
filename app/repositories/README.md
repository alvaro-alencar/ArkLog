# app/repositories — Data Access Layer

Repositories encapsulate all SQL. Services never write SQLAlchemy queries directly — they call repository methods. This keeps business logic testable and makes it possible to swap the DB without touching services.

All repositories extend `BaseRepository[T]` which provides generic `add()` and `get()` methods.

## Files

### `base.py`
Generic async repository with `add(record)` and `get(id)`. All other repositories inherit from this.

### `project_repository.py`
- `get_or_create(project)` — upsert pattern: returns existing `ProjectRecord` or creates one. Called on every webhook push to ensure the project exists in the DB before linking commits.
- `get_by_name(name)` — lookup by project name string.

### `commit_repository.py`
- `exists(sha)` — idempotency guard. Checks if a commit SHA was already processed before persisting.
- `save_commit(commit, project_id)` — persists a `Commit` entity linked to a project.
- `get_since(project_id, since)` — returns all commits after a given datetime, ordered ascending. Used by the scheduler to fetch commits since the last report.

### `report_repository.py`
- `get_by_project(project_id, limit, offset)` — paginated report history.
- `get_latest(project_id)` — most recent report for a project.
- `get_last_generated_at_for_trigger(project_id, trigger)` — returns the `generated_at` of the most recent report with a specific trigger type (`daily_scheduled`, `weekly_scheduled`). This is the continuity mechanism — the scheduler uses this timestamp as the lower bound for the next commit window.
- `get_since(project_id, since)` — reports after a datetime, used for timeline queries.
