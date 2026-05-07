# app/api — HTTP Layer

FastAPI routers. No business logic here — endpoints validate input, call services or repositories, and return responses.

## Structure

```
api/
└── v1/
    ├── router.py        # Aggregates all v1 route modules
    └── routes/
        ├── webhooks.py  # POST /webhooks/github
        ├── projects.py  # GET /projects, GET /projects/{name}/timeline, POST /projects/{name}/backfill
        ├── reports.py   # GET /reports/{id}
        ├── analytics.py # GET /analytics/health
        └── health.py    # GET /health
```

## Routes

### `webhooks.py`
Receives GitHub push events. Validates the `X-Hub-Signature-256` HMAC signature via the `validate_github_signature` FastAPI dependency before processing. Returns HTTP 202 immediately — all processing is async via the event bus.

### `projects.py`
- `GET /projects` — single DB query using 4 correlated scalar subqueries (commit count, report count, last commit, last report) for all projects in one round-trip.
- `GET /projects/{name}/timeline` — daily activity over N days, grouped in Python for SQLite/PostgreSQL portability.
- `POST /projects/{name}/backfill` — runs `backfill_service.backfill_project()` as a `BackgroundTask`, returns 202 immediately.

### `reports.py`
- `GET /reports/{id}` — fetches a single report with its parent project.

### `analytics.py`
- `GET /analytics/health` — health scores and activity metrics per project.

### `health.py`
- `GET /health` — liveness probe. Returns `{"status": "ok"}`.
