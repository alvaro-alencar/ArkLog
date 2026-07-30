"""Shared contracts for ArkLog provider adapters."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ProviderRuntimeError(RuntimeError):
    """Safe provider failure that may be shown to an authenticated user."""


def iso_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_after(value: Any, since: datetime | None) -> bool:
    if since is None:
        return True
    parsed = iso_datetime(value)
    if parsed is None:
        return True
    reference = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
    return parsed >= reference


def chunk_text(text: str, limit: int = 1800) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    remaining = cleaned
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks
