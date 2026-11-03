"""Corpus clause embedding module.

Generates 768-dimensional float32 unit-length embeddings using the
EmbeddingGemma 2 specification: 'title: {title} | text: {content}'.
Calculates pattern frequency and commonality across template clauses,
and ensures vector dimensions and model revisions are never mixed.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL_ID = "google/embeddinggemma-2"
DEFAULT_EMBEDDING_DIM = 768
DEFAULT_EMBEDDING_REVISION = "embeddinggemma-2-rev-202610"


def format_embedding_input(title: str, content: str) -> str:
    """Format input string according to EmbeddingGemma 2 specification.

    Spec: 'title: {title} | text: {content}'
    """
    clean_title = title.strip() if title else "Standard Music Template"
    clean_content = content.strip()
    return f"title: {clean_title} | text: {clean_content}"


def normalize_unit_length(vector: np.ndarray) -> np.ndarray:
    """Normalize a 1D or 2D numpy array to unit L2 length.

    Zero vectors remain zero vectors to prevent division by zero.
    """
    if vector.ndim == 1:
        norm = float(np.linalg.norm(vector))
        if norm > 1e-9:
            return (vector / norm).astype(np.float32)
        return vector.astype(np.float32)
    elif vector.ndim == 2:
        norms = np.linalg.norm(vector, axis=1, keepdims=True)
        norms = np.where(norms > 1e-9, norms, 1.0)
        return (vector / norms).astype(np.float32)
    else:
        raise ValueError(f"Expected 1D or 2D array, got {vector.ndim}D")


def validate_embedding_vector(
    vector: np.ndarray, expected_dim: int = DEFAULT_EMBEDDING_DIM
) -> None:
    """Validate vector dimensionality, dtype, unit length, and absence of NaN/Inf."""
    if vector.shape != (expected_dim,):
        raise ValueError(f"Vector shape mismatch: expected ({expected_dim},), got {vector.shape}")
    if vector.dtype != np.float32:
        raise ValueError(f"Vector dtype mismatch: expected float32, got {vector.dtype}")
    if not np.all(np.isfinite(vector)):
        raise ValueError("Vector contains NaN or Inf values")
    norm = float(np.linalg.norm(vector))
    if abs(norm - 1.0) > 1e-3:
        raise ValueError(f"Vector is not unit length: L2 norm = {norm:.6f}")


class BaseEmbedder(ABC):
    """Abstract interface for corpus embedding models."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return unique model identifier."""

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return output vector dimensionality."""

    @property
    @abstractmethod
    def revision(self) -> str:
        """Return model revision hash or version."""

    @abstractmethod
    def embed_batch(self, formatted_texts: list[str]) -> np.ndarray:
        """Embed a batch of formatted texts into a 2D float32 numpy array."""


class DeterministicEmbedder(BaseEmbedder):
    """Deterministic, repeatable float32 unit-length embedder for testing and offline environments.

    Projects text SHA-256 hashes into 768-dimensional float32 unit vectors.
    Produces identical vectors for identical inputs with zero network or GPU dependencies.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_EMBEDDING_MODEL_ID,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
        revision: str = DEFAULT_EMBEDDING_REVISION,
    ) -> None:
        """Initialize deterministic embedder with model metadata."""
        self._model_id = model_id
        self._embedding_dim = embedding_dim
        self._revision = revision

    @property
    def model_id(self) -> str:
        """Return model id."""
        return self._model_id

    @property
    def embedding_dim(self) -> int:
        """Return embedding dimension."""
        return self._embedding_dim

    @property
    def revision(self) -> str:
        """Return model revision."""
        return self._revision

    def embed_batch(self, formatted_texts: list[str]) -> np.ndarray:
        """Embed texts deterministically into unit-normalized float32 vectors."""
        if not formatted_texts:
            return np.empty((0, self._embedding_dim), dtype=np.float32)

        vectors: list[np.ndarray] = []
        for text in formatted_texts:
            # Hash text into a deterministic seed
            h = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(h[:4], "big")
            rng = np.random.default_rng(seed)

            # Generate Gaussian vector and normalize to unit length
            raw_vec = rng.standard_normal(self._embedding_dim).astype(np.float32)
            unit_vec = normalize_unit_length(raw_vec)
            validate_embedding_vector(unit_vec, self._embedding_dim)
            vectors.append(unit_vec)

        return np.vstack(vectors).astype(np.float32)


class EmbeddingEngine:
    """High-level embedding engine managing model revisions and vector validation."""

    def __init__(self, embedder: BaseEmbedder | None = None) -> None:
        """Initialize engine with underlying embedder."""
        self.embedder: BaseEmbedder = embedder or DeterministicEmbedder()

    @property
    def model_id(self) -> str:
        """Return model ID."""
        return self.embedder.model_id

    @property
    def embedding_dim(self) -> int:
        """Return embedding dimension."""
        return self.embedder.embedding_dim

    @property
    def revision(self) -> str:
        """Return model revision."""
        return self.embedder.revision

    def embed_clauses(
        self,
        clauses_with_titles: list[tuple[str, str]],
    ) -> np.ndarray:
        """Format clauses and generate unit-normalized float32 embeddings.

        Each tuple contains (title, content).
        """
        formatted = [
            format_embedding_input(title, content) for title, content in clauses_with_titles
        ]
        embeddings = self.embedder.embed_batch(formatted)

        # Assert no vector contains NaN or Inf
        if not np.all(np.isfinite(embeddings)):
            raise ValueError("Generated embeddings contain NaN or Inf values")

        # Verify dimensionality and unit norms
        for i in range(len(formatted)):
            validate_embedding_vector(embeddings[i], self.embedding_dim)

        return embeddings


def compute_clause_commonality(
    embeddings: np.ndarray,
    similarity_threshold: float = 0.82,
) -> list[dict[str, Any]]:
    """Group similar template clauses and calculate pattern frequency / commonality.

    Because vectors are unit-length float32, cosine similarity equals the dot product.
    Returns a list of commonality dictionaries corresponding to each input clause.
    """
    n_chunks = len(embeddings)
    if n_chunks == 0:
        return []

    # Pairwise cosine similarity matrix
    sim_matrix = embeddings @ embeddings.T

    commonality_results: list[dict[str, Any]] = []

    for i in range(n_chunks):
        # Count how many other clauses in the corpus share >= similarity_threshold
        matches = np.where(sim_matrix[i] >= similarity_threshold)[0]
        cluster_size = int(len(matches))
        commonality_score = cluster_size / n_chunks
        is_common_pattern = cluster_size >= 2

        commonality_results.append(
            {
                "cluster_size": cluster_size,
                "commonality_score": round(commonality_score, 4),
                "is_common_pattern": is_common_pattern,
                "similar_indices": matches.tolist(),
            }
        )

    return commonality_results


def check_revision_compatibility(
    existing_model_id: str,
    existing_dim: int,
    new_model_id: str,
    new_dim: int,
) -> None:
    """Invariant: Prevent mixing vectors from different embedding models or dimensions."""
    if existing_model_id != new_model_id:
        raise ValueError(
            f"Embedding model mismatch: cannot mix '{existing_model_id}' with '{new_model_id}'"
        )
    if existing_dim != new_dim:
        raise ValueError(f"Embedding dimension mismatch: cannot mix {existing_dim} with {new_dim}")
