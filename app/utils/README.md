# app/utils — Shared Utilities

Small, dependency-free helpers used across the application.

## Files

### `datetime_utils.py`
- `naive_utcnow()` — returns current UTC time without timezone info. SQLite does not store timezone data; using timezone-aware datetimes causes comparison failures. Always use this instead of `datetime.utcnow()` or `datetime.now(timezone.utc)`.
- `parse_github_timestamp(ts)` — converts GitHub's ISO 8601 timestamps (with `Z` or `+00:00` suffix) to naive UTC `datetime` objects.

### `clickup_formatter.py`
Converts AI-generated Markdown reports to visually structured plain text for ClickUp comments. The ClickUp task comment API only accepts plain text (`comment_text`) — rich text delta format is not supported via the public API.

Conversion rules:
| Markdown | Plain text output |
|---|---|
| `## Title` | `\nTITLE` (uppercase) |
| `### Subtitle` | `\n◆ Subtitle` |
| `- item` | `  • item` |
| `**bold**` | `bold` (markers stripped) |
| `*italic*` | `italic` (markers stripped) |
| `---` | *(empty line)* |
