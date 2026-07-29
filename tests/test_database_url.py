"""Database URL compatibility tests for Neon and local development."""

from app.models.database import normalize_database_url


def test_normalizes_standard_neon_url_for_asyncpg() -> None:
    source = (
        "postgresql://user:secret@ep-example-pooler.example.neon.tech/neondb"
        "?channel_binding=require&sslmode=require"
    )
    normalized = normalize_database_url(source)

    assert normalized.startswith("postgresql+asyncpg://")
    assert "channel_binding" not in normalized
    assert "sslmode=require" in normalized


def test_preserves_existing_asyncpg_url_without_channel_binding() -> None:
    source = "postgresql+asyncpg://user:secret@example.test/db?sslmode=require"
    assert normalize_database_url(source) == source


def test_preserves_sqlite_url() -> None:
    source = "sqlite+aiosqlite:///./data/arklog.db"
    assert normalize_database_url(source) == source
