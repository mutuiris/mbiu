"""Tests for health check endpoints (/healthz and /readyz)."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from django.db.utils import DatabaseError
from django.test import Client

from mbiu.corpus.loader import (
    CorpusSnapshot,
    clear_corpus_snapshot,
)


@pytest.fixture(autouse=True)
def _reset_corpus_snapshot() -> Generator[None]:
    """Ensure in-memory corpus snapshot is cleared before and after each test."""
    clear_corpus_snapshot()
    yield
    clear_corpus_snapshot()


def test_healthz() -> None:
    """Liveness probe /healthz returns 200 without checking external dependencies."""
    response = Client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_fails_when_corpus_snapshot_not_loaded() -> None:
    """Readiness probe /readyz returns 503 with 'corpus' in failed when snapshot is None."""
    with patch("django.db.connection.cursor"):
        response = Client().get("/readyz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "corpus" in data["failed"]


def test_readyz_fails_when_database_unreachable() -> None:
    """Readiness probe /readyz returns 503 with 'database' in failed on DatabaseError."""
    # Mock active snapshot loaded, but database down
    fake_snapshot = CorpusSnapshot(
        version_id="fake-id",
        version_tag="v1.0.0",
        embedding_model_id="google/embeddinggemma-2",
        embedding_dim=768,
        embeddings=np.empty((0, 768), dtype=np.float32),
        chunks=(),
        by_id={},
    )
    with patch("mbiu.health.get_active_corpus_snapshot", return_value=fake_snapshot):
        with patch(
            "django.db.connection.cursor", side_effect=DatabaseError("DB connection failed")
        ):
            response = Client().get("/readyz")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["failed"] == ["database"]


def test_readyz_fails_with_multiple_dependencies_when_both_fail() -> None:
    """Readiness probe lists all failed dependencies when both database and corpus fail."""
    with patch("django.db.connection.cursor", side_effect=DatabaseError("DB down")):
        response = Client().get("/readyz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "database" in data["failed"]
        assert "corpus" in data["failed"]


def test_readyz_succeeds_when_database_and_corpus_ready() -> None:
    """Readiness probe returns 200 when database and corpus snapshot are both usable."""
    fake_snapshot = CorpusSnapshot(
        version_id="fake-id",
        version_tag="v1.0.0",
        embedding_model_id="google/embeddinggemma-2",
        embedding_dim=768,
        embeddings=np.empty((0, 768), dtype=np.float32),
        chunks=(),
        by_id={},
    )
    cursor_mock = MagicMock()
    with patch("django.db.connection.cursor", return_value=cursor_mock):
        with patch("mbiu.health.get_active_corpus_snapshot", return_value=fake_snapshot):
            response = Client().get("/readyz")
            assert response.status_code == 200
            assert response.json() == {"status": "ready"}
