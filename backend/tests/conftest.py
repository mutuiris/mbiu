import os

import psycopg
import pytest
from django.conf import settings


def _database_reachable() -> bool:
    db = settings.DATABASES["default"]
    try:
        psycopg.connect(
            host=str(db["HOST"]),
            port=str(db["PORT"]),
            user=str(db["USER"]),
            password=str(db["PASSWORD"]),
            dbname=str(db["NAME"]),
            connect_timeout=2,
        ).close()
    except psycopg.Error:
        return False
    return True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Outside CI, skip database tests when no Postgres is running. CI always runs them."""
    db_items = [item for item in items if "django_db" in item.keywords]
    if not db_items or os.environ.get("CI") or _database_reachable():
        return
    skip = pytest.mark.skip(reason="No Postgres reachable: run `just dev`, or rely on CI")
    for item in db_items:
        item.add_marker(skip)
