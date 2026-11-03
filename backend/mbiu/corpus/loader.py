"""In-memory corpus snapshot loader and accessor.

Loads the active corpus version from the database into in-memory data structures
(numpy arrays for embeddings + metadata lookups) once at startup.
Zero Contract Storage Invariant: The database holds ONLY reviewed template standards.
The active snapshot is loaded into memory so the database is never on the user evaluation path.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
from django.db.utils import DatabaseError

from mbiu.corpus.models import CorpusVersion, ReferenceChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChunkMetadata:
    """In-memory representation of a reference standard chunk."""

    chunk_id: str
    version_tag: str
    source_title: str
    source_license: str
    topic: str
    contract_type: str
    jurisdiction: str
    drafted_for: str
    chunk_key: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class CorpusSnapshot:
    """In-memory snapshot of the active reference template corpus."""

    version_id: str
    version_tag: str
    embedding_model_id: str
    embedding_dim: int
    embeddings: np.ndarray  # Shape: (N, embedding_dim), dtype: np.float32
    chunks: tuple[ChunkMetadata, ...]
    by_id: dict[str, ChunkMetadata]

    @property
    def total_chunks(self) -> int:
        """Return total number of chunks in this snapshot."""
        return len(self.chunks)

    def get_chunk(self, chunk_id: str) -> ChunkMetadata | None:
        """Look up a chunk by its ID."""
        return self.by_id.get(chunk_id)


_SNAPSHOT_LOCK = threading.Lock()
_ACTIVE_SNAPSHOT: CorpusSnapshot | None = None


def get_active_corpus_snapshot() -> CorpusSnapshot | None:
    """Return the currently loaded in-memory active corpus snapshot, or None if not loaded."""
    return _ACTIVE_SNAPSHOT


def clear_corpus_snapshot() -> None:
    """Clear the active in-memory corpus snapshot (primarily for testing)."""
    global _ACTIVE_SNAPSHOT
    with _SNAPSHOT_LOCK:
        _ACTIVE_SNAPSHOT = None


def load_corpus_snapshot() -> CorpusSnapshot | None:
    """Load the active corpus version from the database into memory.

    Queries the active CorpusVersion and all associated ReferenceChunk rows.
    Converts chunk embeddings into a 2D numpy array and indexes metadata by ID.
    Returns the created CorpusSnapshot, or None if no active version exists or on DB error.
    """
    global _ACTIVE_SNAPSHOT

    with _SNAPSHOT_LOCK:
        try:
            active_version = CorpusVersion.objects.filter(is_active=True).first()
            if active_version is None:
                _ACTIVE_SNAPSHOT = None
                return None

            chunks_qs = (
                ReferenceChunk.objects.filter(corpus_version=active_version)
                .select_related("source")
                .order_by("created_at")
            )

            chunk_meta_list: list[ChunkMetadata] = []
            embeddings_list: list[list[float]] = []
            by_id_map: dict[str, ChunkMetadata] = {}

            for chunk in chunks_qs:
                meta = ChunkMetadata(
                    chunk_id=str(chunk.id),
                    version_tag=active_version.version_tag,
                    source_title=chunk.source.title if chunk.source else "",
                    source_license=chunk.source.license if chunk.source else "",
                    topic=chunk.topic,
                    contract_type=chunk.contract_type,
                    jurisdiction=chunk.jurisdiction,
                    drafted_for=chunk.drafted_for,
                    chunk_key=chunk.chunk_key,
                    text=chunk.text,
                    metadata=dict(chunk.metadata) if chunk.metadata else {},
                )
                chunk_meta_list.append(meta)
                by_id_map[str(chunk.id)] = meta

                if chunk.embedding is not None:
                    if isinstance(chunk.embedding, np.ndarray):
                        embeddings_list.append(chunk.embedding.tolist())
                    else:
                        embeddings_list.append(list(chunk.embedding))
                else:
                    embeddings_list.append([0.0] * active_version.embedding_dim)

            if embeddings_list:
                embeddings_array = np.array(embeddings_list, dtype=np.float32)
            else:
                embeddings_array = np.empty((0, active_version.embedding_dim), dtype=np.float32)

            snapshot = CorpusSnapshot(
                version_id=str(active_version.id),
                version_tag=active_version.version_tag,
                embedding_model_id=active_version.embedding_model_id,
                embedding_dim=active_version.embedding_dim,
                embeddings=embeddings_array,
                chunks=tuple(chunk_meta_list),
                by_id=by_id_map,
            )
            _ACTIVE_SNAPSHOT = snapshot
            return snapshot

        except (DatabaseError, Exception) as exc:
            logger.warning("Failed to load active corpus snapshot: %s", exc)
            _ACTIVE_SNAPSHOT = None
            return None
