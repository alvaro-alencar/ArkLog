# app/schemas — API Schemas

Pydantic models for HTTP request/response serialization. Separate from domain entities — schemas are shaped for the API contract, entities are shaped for business logic.

## Files

### `project.py`
- `ProjectSummary` — one project in the list response (name, repo, stats from DB)
- `ProjectListResponse` — wrapper with count + list

### `report.py`
- `ReportResponse` — report content + metadata for API consumers

### `timeline.py`
- `TimelineEntry` — one day: date, commit count, report count, summary snippet
- `TimelineResponse` — full timeline for a project over N days

### `analytics.py`
- `ProjectHealthScore` — composite score based on commit frequency, report coverage, and recency
- `HealthResponse` — list of scores across all projects
