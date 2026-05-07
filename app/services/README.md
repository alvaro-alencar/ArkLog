# app/services — Business Logic

Services are the orchestrators. They subscribe to events, coordinate repositories and external adapters, and publish new events. They contain no HTTP logic and no SQL — those belong in `api/` and `repositories/` respectively.

## Files

### `commit_service.py`
Subscriber of `github.push`. Pipeline:
1. Match incoming repo to a configured project via `projects_config.get_by_repo()`
2. Parse commits from the raw webhook payload
3. Persist only new commits (SHA deduplication via `CommitRepository.exists()`)
4. Publish `commit.batch_ready` once per daily destination — each destination gets its own event with the appropriate `clickup_task_id` and `report_style`

### `report_service.py`
Subscriber of `commit.batch_ready`. Pipeline:
1. Generate report via `ReportGenerator.generate(payload)`
2. Persist `ReportRecord` to DB with `session.flush()` to get the `report_id` immediately
3. Publish `report.generated` with `report_id` and destination metadata

The `report_id` is obtained via flush (not commit) before publishing, eliminating the race condition where the publisher might try to update a record that doesn't exist yet.

### `backfill_service.py`
One-shot service invoked by `POST /projects/{name}/backfill`. Pipeline:
1. Fetch all commits from GitHub REST API (paginated)
2. Persist new commits (idempotent — skips existing SHAs)
3. Publish `commit.batch_ready` for each daily destination with `trigger: "backfill"`

Backfill reports use 8,000 token output and a dedicated system prompt optimized for comprehensive historical analysis.

### `analytics_service.py`
Computes project health scores and activity summaries from the DB. Used by `GET /api/v1/analytics/health`. No external calls — pure DB aggregation.
