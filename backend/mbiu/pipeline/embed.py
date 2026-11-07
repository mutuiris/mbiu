"""Embed template clauses and count how common each pattern is."""

from collections.abc import Sequence
from typing import Protocol

import numpy as np
import numpy.typing as npt

from mbiu.corpus.snapshot import EMBEDDING_DIM
from mbiu.pipeline.errors import PipelineError
from mbiu.pipeline.models import TemplateClause

PATTERN_SIMILARITY = 0.85


class Embedder(Protocol):
    """One embedding model; revision names the exact version."""

    model_id: str
    revision: str

    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        """Return one unit-length row per text."""
        ...


def embedding_text(clause: TemplateClause) -> str:
    """The clause as embedded: its heading, when it has one, then its text."""
    return f"{clause.title}\n{clause.text}" if clause.title else clause.text


def embed_clauses(clauses: Sequence[TemplateClause], embedder: Embedder) -> npt.NDArray[np.float32]:
    """Embed every clause and refuse vectors of the wrong shape, NaNs or non-unit length."""
    if not clauses:
        return np.empty((0, EMBEDDING_DIM), dtype=np.float32)
    vectors = embedder.encode([embedding_text(c) for c in clauses])
    if vectors.shape != (len(clauses), EMBEDDING_DIM):
        raise PipelineError(f"expected {len(clauses)} x {EMBEDDING_DIM} vectors")
    if not np.isfinite(vectors).all():
        raise PipelineError("embedding contains NaN or infinity")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-3):
        raise PipelineError("embedding is not unit length")
    return vectors


def pattern_counts(
    vectors: npt.NDArray[np.float32], threshold: float = PATTERN_SIMILARITY
) -> list[int]:
    """For each clause, how many clauses (itself included) are at least ``threshold`` similar."""
    if len(vectors) == 0:
        return []
    return [int(n) for n in ((vectors @ vectors.T) >= threshold).sum(axis=1)]
