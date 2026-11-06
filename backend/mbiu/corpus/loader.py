"""The active corpus, read once into memory so retrieval never queries the database."""

import logging
import threading

import numpy as np
from django.db import DatabaseError

from mbiu.corpus.models import CorpusVersion, ReferenceChunk
from mbiu.corpus.snapshot import EMBEDDING_DIM, CorpusSnapshot, SnapshotChunk

logger = logging.getLogger(__name__)


_lock = threading.Lock()
_snapshot: CorpusSnapshot | None = None


def active_snapshot() -> CorpusSnapshot | None:
    """Return the in-memory corpus, loading it on first use.

    Returns None while no version is active or the database is unreachable; the next
    call tries again. /readyz calls this, so the host's startup probe does the first load.
    """
    global _snapshot
    if _snapshot is None:
        with _lock:
            if _snapshot is None:
                _snapshot = _load()
    return _snapshot


def reset_snapshot() -> None:
    """Forget the loaded corpus, so the next call reloads it (after activating a version)."""
    global _snapshot
    with _lock:
        _snapshot = None


def _load() -> CorpusSnapshot | None:
    try:
        version = CorpusVersion.objects.filter(is_active=True).first()
        if version is None:
            return None
        rows = list(
            ReferenceChunk.objects.filter(corpus_version=version)
            .select_related("source")
            .order_by("chunk_key")
        )
    except DatabaseError:
        logger.warning("Could not load the active corpus", exc_info=True)
        return None

    embeddings = np.array([row.embedding for row in rows], dtype=np.float32).reshape(
        len(rows), EMBEDDING_DIM
    )
    chunks = tuple(
        SnapshotChunk(
            chunk_id=str(row.id),
            chunk_key=row.chunk_key,
            title=row.title,
            text=row.text,
            topic=row.topic,
            contract_type=row.contract_type,
            jurisdiction=row.jurisdiction,
            drafted_for=row.drafted_for,
            pattern_count=row.pattern_count,
            source_title=row.source.title,
            source_url=row.source.url,
            licence=row.source.licence,
            reviewing_body=row.source.reviewing_body,
        )
        for row in rows
    )
    logger.info("Loaded corpus %s with %d chunks", version.version_tag, len(chunks))
    return CorpusSnapshot(
        version_tag=version.version_tag,
        embedding_model_id=version.embedding_model_id,
        embedding_revision=version.embedding_revision,
        embeddings=embeddings,
        chunks=chunks,
    )
