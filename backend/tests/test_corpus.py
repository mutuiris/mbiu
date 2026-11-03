"""Tests for corpus models, zero contract storage invariant, and startup loader."""

import datetime
from collections.abc import Generator
from unittest.mock import patch

import numpy as np
import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.utils import DatabaseError
from django.test import Client

from mbiu.corpus.loader import (
    clear_corpus_snapshot,
    get_active_corpus_snapshot,
    load_corpus_snapshot,
)
from mbiu.corpus.models import (
    CorpusVersion,
    PipelineCheckResult,
    ReferenceChunk,
    ReferenceSource,
)


@pytest.fixture(autouse=True)
def _reset_snapshot() -> Generator[None]:
    """Ensure in-memory snapshot is clean before and after each test."""
    clear_corpus_snapshot()
    yield
    clear_corpus_snapshot()


@pytest.mark.django_db
def test_zero_contract_storage_database_schema() -> None:
    """Zero Contract Storage Invariant: The database schema stores ONLY reference standards.

    Asserts that:
    1. mbiu.corpus contains exactly the four allowed application tables.
    2. No tables or columns exist anywhere in the app for storing user contracts,
       raw uploads, user text, or user evaluation results.
    """
    corpus_app = apps.get_app_config("corpus")
    models = list(corpus_app.get_models())

    # Only four application models are permitted
    assert len(models) == 4
    model_names = {model.__name__ for model in models}
    assert model_names == {
        "ReferenceSource",
        "CorpusVersion",
        "ReferenceChunk",
        "PipelineCheckResult",
    }

    # Verify exact database table names
    table_names = {model._meta.db_table for model in models}
    assert table_names == {
        "reference_sources",
        "corpus_versions",
        "reference_chunks",
        "pipeline_check_results",
    }

    # Verify that no forbidden columns (e.g. user, upload, file, session, raw_contract) exist
    forbidden_terms = ["user_id", "user_contract", "uploaded_file", "session", "contract_file"]
    for model in models:
        field_names = [f.name for f in model._meta.get_fields()]
        for term in forbidden_terms:
            assert term not in field_names, f"Forbidden field '{term}' found in {model.__name__}"


@pytest.mark.django_db
def test_reference_source_lifecycle() -> None:
    """Verify creating ReferenceSource with lawful reuse license and metadata."""
    source = ReferenceSource.objects.create(
        title="WIPO How to Make a Living from Music (3rd Ed)",
        url="https://www.wipo.int/publications/en/details.jsp?id=4681",
        license="CC BY 4.0",
        reviewing_body="WIPO",
        contract_type="management",
        jurisdiction="international",
    )
    assert source.id is not None
    assert str(source) == "WIPO How to Make a Living from Music (3rd Ed) (international)"
    assert source.created_at is not None
    assert source.updated_at is not None


@pytest.mark.django_db
def test_corpus_version_single_active_constraint() -> None:
    """Invariant: Exactly one corpus version can be active (is_active=True) at a time."""
    v1 = CorpusVersion.objects.create(
        version_tag="v1.0.0",
        is_active=True,
        embedding_model_id="google/embeddinggemma-2",
        embedding_dim=768,
    )
    assert str(v1) == "CorpusVersion(v1.0.0) [ACTIVE]"

    # Attempting to save a second active version must fail full_clean()
    v2 = CorpusVersion(
        version_tag="v2.0.0",
        is_active=True,
        embedding_model_id="google/embeddinggemma-2",
        embedding_dim=768,
    )
    with pytest.raises(ValidationError, match="Only one corpus version can be active"):
        v2.save()


@pytest.mark.django_db
def test_corpus_version_database_unique_active_constraint() -> None:
    """Verify the database-level unique constraint on active corpus version."""
    CorpusVersion.objects.create(
        version_tag="v1.0.0",
        is_active=True,
    )

    # Bypass clean() by using bulk_create or objects.filter to verify DB-level constraint
    v2 = CorpusVersion(
        version_tag="v2.0.0",
        is_active=True,
    )
    with pytest.raises((IntegrityError, ValidationError)):
        # Calling super().save() directly triggers the DB constraint
        super(CorpusVersion, v2).save()


@pytest.mark.django_db
def test_corpus_version_atomic_activation() -> None:
    """Verify CorpusVersion.activate_version() atomically flips active pointer."""
    v1 = CorpusVersion.objects.create(version_tag="v1.0.0", is_active=True)
    v2 = CorpusVersion.objects.create(version_tag="v2.0.0", is_active=False)

    CorpusVersion.activate_version("v2.0.0")

    v1.refresh_from_db()
    v2.refresh_from_db()
    assert not v1.is_active
    assert v2.is_active


@pytest.mark.django_db
def test_published_corpus_version_is_immutable() -> None:
    """Invariant: Published corpus versions are never edited in place."""
    published_now = datetime.datetime.now(datetime.UTC)
    version = CorpusVersion.objects.create(
        version_tag="v1.0.0",
        is_active=True,
        published_at=published_now,
    )

    # Editing immutable fields must raise ValidationError
    version.version_tag = "v1.0.1-tampered"
    with pytest.raises(
        ValidationError, match="Published corpus versions cannot be edited in place"
    ):
        version.save()

    # Changing only is_active is permitted for rollback/activation
    version.version_tag = "v1.0.0"
    version.is_active = False
    version.save()
    version.refresh_from_db()
    assert not version.is_active


@pytest.mark.django_db
def test_reference_chunk_and_pipeline_check_relationships() -> None:
    """Verify relationships between sources, versions, chunks, and pipeline check results."""
    source = ReferenceSource.objects.create(
        title="Kenya Copyright Act (Cap. 130)",
        license="Public Sector",
        reviewing_body="KECOBO",
        contract_type="statutory",
        jurisdiction="KE",
    )
    version = CorpusVersion.objects.create(
        version_tag="v1.0.0",
        is_active=True,
    )

    chunk = ReferenceChunk.objects.create(
        corpus_version=version,
        source=source,
        chunk_key="Sec 30A",
        text="Remuneration for broadcasting and communication to the public.",
        topic="royalties",
        contract_type="statutory",
        jurisdiction="KE",
        drafted_for="artist",
        metadata={"section": "Part III", "statute": "Cap. 130"},
        embedding=[0.05] * 768,
    )

    check = PipelineCheckResult.objects.create(
        corpus_version=version,
        check_name="presidio_pii",
        passed=True,
        details={"scanned_chunks": 1, "pii_entities_found": 0},
    )

    assert chunk.id is not None
    assert str(chunk) == "ReferenceChunk(Sec 30A, topic=royalties)"
    assert list(source.chunks.all()) == [chunk]
    assert list(version.chunks.all()) == [chunk]
    assert list(version.pipeline_checks.all()) == [check]
    assert str(check) == "PipelineCheck(presidio_pii=PASSED, version=v1.0.0)"


@pytest.mark.django_db
def test_corpus_loader_behavior_with_seeded_data() -> None:
    """Verify in-memory loader loads numpy embeddings and metadata lookups correctly."""
    source = ReferenceSource.objects.create(
        title="WIPO Example Management Agreement",
        license="CC BY 4.0",
        reviewing_body="WIPO",
        contract_type="management",
        jurisdiction="international",
    )
    version = CorpusVersion.objects.create(
        version_tag="v1.0.0",
        is_active=True,
        embedding_model_id="google/embeddinggemma-2",
        embedding_dim=768,
    )

    # Create 3 reference chunks with distinct embedding vectors
    vec1 = [0.1] * 768
    vec2 = [0.2] * 768
    vec3 = [0.3] * 768

    c1 = ReferenceChunk.objects.create(
        corpus_version=version,
        source=source,
        chunk_key="Clause 1.1",
        text="The Manager shall use reasonable endeavours to promote the Artist.",
        topic="duties",
        contract_type="management",
        jurisdiction="international",
        drafted_for="artist",
        embedding=vec1,
    )
    c2 = ReferenceChunk.objects.create(
        corpus_version=version,
        source=source,
        chunk_key="Clause 4.2",
        text="The Commission shall be 20% of Gross Receipts.",
        topic="commission",
        contract_type="management",
        jurisdiction="international",
        drafted_for="neutral",
        embedding=vec2,
    )
    c3 = ReferenceChunk.objects.create(
        corpus_version=version,
        source=source,
        chunk_key="Clause 9.1",
        text="Either party may terminate upon 30 days written notice.",
        topic="termination",
        contract_type="management",
        jurisdiction="international",
        drafted_for="artist",
        embedding=vec3,
    )

    # Before loading, snapshot is None
    assert get_active_corpus_snapshot() is None

    # Load snapshot
    snapshot = load_corpus_snapshot()
    assert snapshot is not None
    assert get_active_corpus_snapshot() is snapshot

    # Verify snapshot properties
    assert snapshot.version_tag == "v1.0.0"
    assert snapshot.embedding_model_id == "google/embeddinggemma-2"
    assert snapshot.embedding_dim == 768
    assert snapshot.total_chunks == 3

    # Verify numpy array shape and dtype
    assert isinstance(snapshot.embeddings, np.ndarray)
    assert snapshot.embeddings.shape == (3, 768)
    assert snapshot.embeddings.dtype == np.float32
    assert np.isclose(snapshot.embeddings[0, 0], 0.1, atol=1e-5)
    assert np.isclose(snapshot.embeddings[1, 0], 0.2, atol=1e-5)
    assert np.isclose(snapshot.embeddings[2, 0], 0.3, atol=1e-5)

    # Verify metadata and lookups
    assert len(snapshot.chunks) == 3
    assert snapshot.get_chunk(str(c1.id)) is not None
    assert snapshot.get_chunk(str(c3.id)) is not None
    chunk_meta = snapshot.get_chunk(str(c2.id))
    assert chunk_meta is not None
    assert chunk_meta.chunk_key == "Clause 4.2"
    assert chunk_meta.topic == "commission"
    assert chunk_meta.source_title == "WIPO Example Management Agreement"
    assert chunk_meta.source_license == "CC BY 4.0"
    assert chunk_meta.drafted_for == "neutral"

    # Non-existent chunk lookup returns None
    assert snapshot.get_chunk("nonexistent-chunk-id") is None


@pytest.mark.django_db
def test_corpus_loader_when_no_active_version() -> None:
    """Verify loader returns None when no version is active."""
    CorpusVersion.objects.create(version_tag="v1.0.0", is_active=False)
    snapshot = load_corpus_snapshot()
    assert snapshot is None
    assert get_active_corpus_snapshot() is None


@pytest.mark.django_db
def test_corpus_loader_empty_active_version() -> None:
    """Verify loader handles an active version with zero chunks cleanly."""
    CorpusVersion.objects.create(
        version_tag="v1.0.0",
        is_active=True,
        embedding_dim=768,
    )
    snapshot = load_corpus_snapshot()
    assert snapshot is not None
    assert snapshot.total_chunks == 0
    assert snapshot.embeddings.shape == (0, 768)
    assert snapshot.embeddings.dtype == np.float32


@pytest.mark.django_db
def test_corpus_loader_catches_database_error() -> None:
    """Verify loader safely handles database errors, logs warning, and sets snapshot to None."""
    with patch(
        "mbiu.corpus.models.CorpusVersion.objects.filter",
        side_effect=DatabaseError("Query failed"),
    ):
        snapshot = load_corpus_snapshot()
        assert snapshot is None
        assert get_active_corpus_snapshot() is None


@pytest.mark.django_db
def test_readyz_integration_with_database_and_corpus_loader() -> None:
    """End-to-end integration test: /readyz transitions from 503 to 200 once corpus is loaded."""
    client = Client()

    # Step 1: No active version in DB -> /readyz returns 503 with failed=['corpus']
    load_corpus_snapshot()
    res1 = client.get("/readyz")
    assert res1.status_code == 503
    assert res1.json() == {"status": "not_ready", "failed": ["corpus"]}

    # Step 2: Seed active version with a chunk and load snapshot -> /readyz returns 200
    version = CorpusVersion.objects.create(version_tag="v1.0.0", is_active=True)
    ReferenceChunk.objects.create(
        corpus_version=version,
        text="Template text",
        topic="term",
        contract_type="recording",
        embedding=[0.0] * 768,
    )
    load_corpus_snapshot()

    res2 = client.get("/readyz")
    assert res2.status_code == 200
    assert res2.json() == {"status": "ready"}
