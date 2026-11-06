"""Embed template clauses with EmbeddingGemma 2 and count how common each pattern is."""

import importlib
from collections.abc import Sequence
from typing import Protocol

import numpy as np
import numpy.typing as npt

from mbiu.corpus.models import EMBEDDING_DIM
from mbiu.pipeline.errors import ConfigurationError, PipelineError
from mbiu.pipeline.models import TemplateClause

PATTERN_SIMILARITY = 0.85


class Embedder(Protocol):
    """One embedding model at one pinned revision."""

    model_id: str
    revision: str

    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        """Return one unit-length row per text."""
        ...


class EmbeddingGemma:
    """EmbeddingGemma 2 through sentence-transformers, on CPU in float32."""

    def __init__(self, model_id: str, revision: str) -> None:
        """Load the model at an exact commit, so every vector in a version matches."""
        if not model_id or not revision:
            raise ConfigurationError("EMBEDDING_MODEL_ID and EMBEDDING_REVISION are required")
        sentence_transformers = importlib.import_module("sentence_transformers")
        model = sentence_transformers.SentenceTransformer(model_id, revision=revision, device="cpu")
        self._model = model.float()
        self.model_id = model_id
        self.revision = revision

    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        """Embed already formatted document texts."""
        vectors = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(vectors, dtype=np.float32)


def embedding_text(clause: TemplateClause) -> str:
    """EmbeddingGemma's document format; ``none`` stands in for a missing title."""
    return f"title: {clause.title or 'none'} | text: {clause.text}"


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
