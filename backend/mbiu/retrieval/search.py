"""Hybrid search over the in-memory corpus: meaning (vectors) plus exact words (BM25)."""

import re
import threading
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt
from rank_bm25 import BM25Plus

from mbiu.corpus.snapshot import CorpusSnapshot, SnapshotChunk

# Standard reciprocal rank fusion constant: dampens the weight of top ranks
RRF_K: Final = 60
HOME_JURISDICTION: Final = "KE"

_WORD = re.compile(r"\w+")
_bm25_lock = threading.Lock()
_bm25_by_version: dict[str, BM25Plus] = {}


@dataclass(frozen=True)
class Match:
    """A template chunk and how well it matched."""

    chunk: SnapshotChunk
    score: float


def tokens(text: str) -> list[str]:
    """Lowercase words, the unit BM25 counts."""
    return _WORD.findall(text.lower())


def _bm25(snapshot: CorpusSnapshot) -> BM25Plus:
    # BM25Plus, not Okapi: Okapi gives a word zero weight when it is in half the documents,
    # which wipes out matches in a small corpus. One index per corpus version.
    with _bm25_lock:
        index = _bm25_by_version.get(snapshot.version_tag)
        if index is None:
            index = BM25Plus([tokens(c.text) for c in snapshot.chunks])
            _bm25_by_version[snapshot.version_tag] = index
        return index


def _ranks(scores: npt.NDArray[np.float64]) -> npt.NDArray[np.int64]:
    """Rank of each position, 0 for the best score."""
    ranks = np.empty(len(scores), dtype=np.int64)
    ranks[np.argsort(-scores, kind="stable")] = np.arange(len(scores))
    return ranks


def search(
    snapshot: CorpusSnapshot,
    query_text: str,
    query_vector: npt.NDArray[np.float32] | None,
    *,
    contract_type: str | None = None,
    k: int = 5,
) -> list[Match]:
    """Return up to k template chunks for a clause, Kenyan sources first.

    Chunks of the contract's type are searched when there are any, otherwise all chunks.
    Without a query vector (no embedder) the search falls back to BM25 alone.
    """
    if not snapshot.chunks or k <= 0:
        return []

    all_indices = np.arange(len(snapshot.chunks))
    candidates = all_indices
    if contract_type:
        same_type = all_indices[[c.contract_type == contract_type for c in snapshot.chunks]]
        if same_type.size:
            candidates = same_type

    bm25 = np.asarray(_bm25(snapshot).get_scores(tokens(query_text)), dtype=np.float64)
    fused = 1.0 / (RRF_K + _ranks(bm25[candidates]))
    if query_vector is not None:
        cosine = (snapshot.embeddings[candidates] @ query_vector).astype(np.float64)
        fused = fused + 1.0 / (RRF_K + _ranks(cosine))

    # Keep the strongest 2k, then put Kenyan sources ahead of foreign ones among them
    shortlist = np.argsort(-fused, kind="stable")[: 2 * k]
    ordered = sorted(
        shortlist,
        key=lambda i: (snapshot.chunks[candidates[i]].jurisdiction != HOME_JURISDICTION, -fused[i]),
    )
    return [Match(chunk=snapshot.chunks[candidates[i]], score=float(fused[i])) for i in ordered[:k]]
