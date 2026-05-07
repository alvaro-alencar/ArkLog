# app/schedulers — Scheduled Report Jobs

APScheduler-based cron engine for time-triggered reports. All jobs are stored in the DB (`apscheduler_jobs` table) — this makes scheduling distributed-safe: multiple ArkLog instances sharing the same DB will not duplicate jobs.

## Files

### `scheduler.py`
Creates and exports the `AsyncIOScheduler` singleton with a `SQLAlchemyJobStore`. The job store URL is derived from `DATABASE_URL` by replacing the async driver with its sync equivalent (APScheduler requires a sync connection for job persistence).

Set `SCHEDULER_ENABLED=false` on replica containers as an additional safety valve when running multiple instances.

### `report_scheduler.py`
Registers one cron job per project per `ReportDestination` on startup. Two trigger types:

| Destination `schedule` | APScheduler trigger | DB trigger value |
|---|---|---|
| `daily` | `cron(hour=H, minute=M)` | `daily_scheduled` |
| `weekly` | `cron(day_of_week="fri", hour=H, minute=M)` | `weekly_scheduled` |

**Continuity mechanism** — `_run_scheduled_report`:
1. Queries `report_repository.get_last_generated_at_for_trigger(project_id, trigger)`
2. Uses that timestamp as `since` for `commit_repository.get_since()`
3. First run (no previous report): `since = datetime(2000, 1, 1)` → fetches all commits in DB
4. Publishes `commit.batch_ready` with the fetched commits

`misfire_grace_time`: 5 minutes for daily jobs, 1 hour for weekly jobs. If ArkLog was down when a job was scheduled, APScheduler will still fire it within the grace window after restart.
