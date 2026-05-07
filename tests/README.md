# tests/ — Test Suite

```bash
pytest                          # run all tests
pytest tests/test_timeline_api.py -v   # run one file
pytest -k "scheduler" -v        # run by keyword
```

## Files

### `test_clickup_publisher.py`
Unit tests for `ClickUpPublisher`. Verifies header formatting, Brasília timestamp, trigger label ("N commit(s) analyzed" vs "scheduled checkpoint"), and the race-condition-safe `_mark_published` flow using a real `report_id`.

### `test_report_scheduler.py`
Tests for `_run_scheduled_report`. Covers:
- Continuity: uses `get_last_generated_at_for_trigger` as the `since` bound
- First run (no previous report): defaults to `datetime(2000, 1, 1)` to fetch all commits
- Correct trigger value passed through to the event payload

### `test_timeline_api.py`
Integration tests for `GET /projects/{name}/timeline`. Verifies the dense date range (all days including zeros), correct grouping by date, and 404 behavior for unknown projects.

## Conventions

- Use `pytest-asyncio` for async tests
- Fixtures live in `conftest.py` (to be created)
- Mock external HTTP calls (GitHub API, ClickUp API, OpenRouter) — never make real network calls in tests
- DB tests use an in-memory SQLite database
