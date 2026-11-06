from collections.abc import Iterator

import numpy as np
import pytest
from django.db import IntegrityError, connection, transaction
from django.test import Client

from mbiu.corpus.loader import active_snapshot, reset_snapshot
from mbiu.corpus.models import EMBEDDING_DIM, CorpusVersion, ReferenceChunk, ReferenceSource

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_snapshot() -> Iterator[None]:
    reset_snapshot()
    yield
    reset_snapshot()


def _seed(version_tag: str, chunk_count: int = 2) -> CorpusVersion:
    source = ReferenceSource.objects.create(
        title="Synthetic recording agreement",
        url="https://example.org/synthetic.pdf",
        document_sha256="a" * 64,
        licence="CC BY 4.0",
        reviewing_body="Example Musicians' Union",
        template_version="1",
        contract_type="recording",
        jurisdiction="KE",
    )
    version = CorpusVersion.objects.create(
        version_tag=version_tag,
        embedding_model_id="google/embeddinggemma-2",
        embedding_revision="test",
    )
    for n in range(chunk_count):
        ReferenceChunk.objects.create(
            corpus_version=version,
            source=source,
            chunk_key=f"KE-RECORDING-{n:02d}",
            text=f"The Label shall pay the Artist a royalty of {15 + n}% of gross receipts.",
            topic="royalties",
            contract_type="recording",
            jurisdiction="KE",
            drafted_for="neutral",
            embedding=np.full(EMBEDDING_DIM, n + 1, dtype=np.float32),
        )
    return version


def test_readyz_fails_with_corpus_until_a_version_is_active() -> None:
    response = Client().get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "failed": ["corpus"]}

    _seed("v1")
    CorpusVersion.activate("v1")
    reset_snapshot()

    response = Client().get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_active_version_loads_into_memory_with_provenance() -> None:
    _seed("v1", chunk_count=1)
    _seed("v2", chunk_count=3)
    CorpusVersion.activate("v2")

    snapshot = active_snapshot()

    assert snapshot is not None
    assert snapshot.version_tag == "v2"
    assert snapshot.embeddings.shape == (3, EMBEDDING_DIM)
    assert snapshot.embeddings.dtype == np.float32
    assert [c.chunk_key for c in snapshot.chunks] == [
        "KE-RECORDING-00",
        "KE-RECORDING-01",
        "KE-RECORDING-02",
    ]
    # Row i of the matrix belongs to chunk i
    assert snapshot.embeddings[2][0] == 3.0
    assert snapshot.chunks[0].licence == "CC BY 4.0"
    assert snapshot.chunks[0].reviewing_body == "Example Musicians' Union"


def test_only_one_version_can_be_active() -> None:
    _seed("v1")
    _seed("v2")
    CorpusVersion.activate("v1")
    with pytest.raises(IntegrityError), transaction.atomic():
        CorpusVersion.objects.filter(version_tag="v2").update(is_active=True)


def test_activate_moves_the_pointer_in_one_step() -> None:
    _seed("v1")
    _seed("v2")
    CorpusVersion.activate("v1")
    CorpusVersion.activate("v2")
    assert list(
        CorpusVersion.objects.filter(is_active=True).values_list("version_tag", flat=True)
    ) == ["v2"]


def test_row_level_security_is_on_for_all_four_tables() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname = ANY(%s)",
            [
                [
                    "reference_sources",
                    "corpus_versions",
                    "reference_chunks",
                    "pipeline_check_results",
                ]
            ],
        )
        rows = dict(cursor.fetchall())
    assert rows == {
        "reference_sources": True,
        "corpus_versions": True,
        "reference_chunks": True,
        "pipeline_check_results": True,
    }
