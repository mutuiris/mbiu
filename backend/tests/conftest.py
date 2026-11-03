"""Pytest configuration and fixtures for Mbiu tests."""

import pytest
from django.conf import settings


def pytest_configure(config: pytest.Config) -> None:
    """Configure test environment and database connection.

    If PostgreSQL is unreachable (e.g. running unit tests locally without docker),
    fall back to in-memory SQLite to keep local developer iteration instant and hermetic.
    In CI and with Docker running, PostgreSQL with pgvector is used.
    """
    db_config = settings.DATABASES.get("default", {})
    if db_config.get("ENGINE") == "django.db.backends.postgresql":
        try:
            import psycopg

            conn = psycopg.connect(
                host=str(db_config.get("HOST") or "localhost"),
                port=int(str(db_config.get("PORT") or 5432)),
                user=str(db_config.get("USER") or "mbiu"),
                password=str(db_config.get("PASSWORD") or ""),
                dbname=str(db_config.get("NAME") or "mbiu"),
                connect_timeout=1,
            )
            conn.close()
        except Exception:
            # PostgreSQL is not running locally; use fast in-memory SQLite for tests
            settings.DATABASES["default"] = {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
