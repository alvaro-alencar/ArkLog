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
    assert "sslmode" not in normalized
    assert "ssl=require" in normalized


def test_translates_existing_asyncpg_sslmode() -> None:
    source = "postgresql+asyncpg://user:secret@example.test/db?sslmode=verify-full"
    assert normalize_database_url(source).endswith("?ssl=verify-full")


def test_preserves_explicit_asyncpg_ssl_parameter() -> None:
    source = (
        "postgresql+asyncpg://user:secret@example.test/db"
        "?ssl=verify-full&sslmode=require"
    )
    normalized = normalize_database_url(source)

    assert normalized.endswith("?ssl=verify-full")
    assert "sslmode" not in normalized


def test_preserves_sqlite_url() -> None:
    source = "sqlite+aiosqlite:///./data/arklog.db"
    assert normalize_database_url(source) == source
