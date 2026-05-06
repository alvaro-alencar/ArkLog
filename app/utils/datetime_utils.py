"""ArkLog - Datetime Utilities."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def naive_utcnow() -> datetime:
    """Return current UTC time as timezone-naive datetime (required for SQLite column defaults)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_github_timestamp(ts: str) -> datetime:
    """Parse ISO 8601 timestamps from GitHub API responses."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def format_duration(seconds: float) -> str:
    """Human-readable duration from seconds."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"
