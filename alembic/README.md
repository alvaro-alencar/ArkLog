# alembic/ — Database Migrations

Schema version control via Alembic with async SQLAlchemy support.

## Common Commands

```bash
# Apply all pending migrations (run on first setup and after pulling new versions)
alembic upgrade head

# Create a new migration after changing app/models/tables.py
alembic revision --autogenerate -m "add_column_x_to_table_y"

# Check current DB version
alembic current

# Downgrade one step
alembic downgrade -1
```

## Files

### `env.py`
Alembic environment configuration. Uses `asyncio.run()` to bridge the async SQLAlchemy engine with Alembic's sync migration runner. Imports `Base` and `settings` from the app to auto-detect schema changes.

### `versions/`
One file per migration. Filename format: `YYYYMMDD_NNNN_description.py`.

## Notes

- Migrations run against the URL in `DATABASE_URL` (from `.env`)
- SQLite is the default for development; PostgreSQL is recommended for production
- If you set up a fresh database (no existing `alembic_version` table), just run `alembic upgrade head` — it creates everything from scratch
