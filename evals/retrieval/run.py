"""Measure recall@k for retrieval and compare two query task types.

python -m evals.retrieval.run            # BM25 only, no API key needed
python -m evals.retrieval.run --embed    # with gemini-embedding-2 (needs GEMINI_API_KEY)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from mbiu.corpus.snapshot import CorpusSnapshot, SnapshotChunk
from mbiu.retrieval.embed import GeminiEmbedder, Task
from mbiu.retrieval.search import search

DATASET = Path(__file__).with_name("dataset.json")
QUERY_TASKS: tuple[Task, ...] = ("RETRIEVAL_QUERY", "FACT_VERIFICATION")


def _snapshot(
    templates: list[dict[str, str]], vectors: npt.NDArray[np.float32]
) -> CorpusSnapshot:
    chunks = tuple(
        SnapshotChunk(
            chunk_id=t["key"],
            chunk_key=t["key"],
            title=t["title"],
            text=t["text"],
            topic="",
            contract_type=t["contract_type"],
            jurisdiction=t["jurisdiction"],
            drafted_for="neutral",
            pattern_count=1,
            source_title="Synthetic",
            source_url="",
            licence="",
            reviewing_body="",
        )
        for t in templates
    )
    return CorpusSnapshot("eval", "eval", "eval", vectors, chunks)


def recall_at_k(
    snapshot: CorpusSnapshot,
    queries: list[dict[str, str]],
    query_vectors: npt.NDArray[np.float32] | None,
    k: int,
) -> float:
    """Share of queries whose expected template is in the top k."""
    hits = 0
    for i, q in enumerate(queries):
        vector = None if query_vectors is None else query_vectors[i]
        found = search(
            snapshot, q["text"], vector, contract_type=q["contract_type"], k=k
        )
        hits += any(m.chunk.chunk_key == q["expected"] for m in found)
    return hits / len(queries)


def main(argv: list[str] | None = None) -> int:
    """Print recall@k for BM25 alone, or for each query prefix with embeddings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--min-recall", type=float, default=0.0, help="fail below this recall"
    )
    parser.add_argument(
        "--embed", action="store_true", help="also use gemini-embedding-2 vectors"
    )
    args = parser.parse_args(argv)

    data: dict[str, Any] = json.loads(DATASET.read_text(encoding="utf-8"))
    templates, queries = data["templates"], data["queries"]

    if not args.embed:
        empty = np.zeros((len(templates), 1), dtype=np.float32)
        recall = recall_at_k(_snapshot(templates, empty), queries, None, args.k)
        print(f"BM25 only: recall@{args.k} = {recall:.2f}")
        return 0 if recall >= args.min_recall else 1

    from google import genai

    embedder = GeminiEmbedder(
        genai.Client(api_key=os.environ["GEMINI_API_KEY"]),
        os.environ.get("EMBEDDING_MODEL_ID", "gemini-embedding-2"),
    )
    docs = [f"{t['title']}\n{t['text']}" for t in templates]

    async def embed_all() -> list[npt.NDArray[np.float32]]:
        # One event loop for every call: the SDK's async client is bound to the first loop
        doc_vectors = await embedder.embed(docs, "RETRIEVAL_DOCUMENT")
        texts = [q["text"] for q in queries]
        return [doc_vectors] + [
            await embedder.embed(texts, task) for task in QUERY_TASKS
        ]

    doc_vectors, *query_vectors = asyncio.run(embed_all())
    snapshot = _snapshot(templates, doc_vectors)
    worst = 1.0
    for task, vectors in zip(QUERY_TASKS, query_vectors, strict=True):
        recall = recall_at_k(snapshot, queries, vectors, args.k)
        worst = min(worst, recall)
        print(f"{task}: recall@{args.k} = {recall:.2f}")
    return 0 if worst >= args.min_recall else 1


if __name__ == "__main__":
    raise SystemExit(main())
