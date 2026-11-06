"""The in-memory corpus shape, kept free of Django so scripts and evals can build one."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

EMBEDDING_DIM = 768


@dataclass(frozen=True)
class SnapshotChunk:
    """One reference chunk with the provenance a result card needs."""

    chunk_id: str
    chunk_key: str
    title: str
    text: str
    topic: str
    contract_type: str
    jurisdiction: str
    drafted_for: str
    pattern_count: int
    source_title: str
    source_url: str
    licence: str
    reviewing_body: str


@dataclass(frozen=True)
class CorpusSnapshot:
    """The active version: row i of embeddings belongs to chunks[i]."""

    version_tag: str
    embedding_model_id: str
    embedding_revision: str
    embeddings: npt.NDArray[np.float32]
    chunks: tuple[SnapshotChunk, ...]
