"""For each contract clause: the template evidence to compare with, and its topic."""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt
from opentelemetry import trace

from mbiu.api.schemas import Evidence
from mbiu.corpus.loader import active_snapshot
from mbiu.corpus.synthetic import retrieve_simple_evidence
from mbiu.llm import LLMError
from mbiu.retrieval.embed import embedder
from mbiu.retrieval.search import Match, search
from mbiu.retrieval.topics import TOPIC_EXAMPLES, classify

logger = logging.getLogger(__name__)
tracer: Final = trace.get_tracer("mbiu.retrieval")

# The model is sent one template per clause, so only the best match is kept
EVIDENCE_PER_CLAUSE: Final = 1
NO_STANDARD_NOTE: Final = (
    "Mbiu doesn't have a reviewed standard for this kind of contract yet, "
    "so it can explain these clauses but not compare them."
)
SYNTHETIC_CORPUS_VERSION: Final = "synthetic"

_EXAMPLE_TOPICS: Final[tuple[str, ...]] = tuple(
    topic for topic, examples in TOPIC_EXAMPLES.items() for _ in examples
)
_example_vectors: npt.NDArray[np.float32] | None = None


@dataclass(frozen=True)
class ClausePlan:
    """What a clause is compared with, and its topic (None when it couldn't be classified).

    note is set when there is nothing to compare with, and says why.
    """

    evidence: list[Evidence]
    topic: str | None
    note: str | None = None


def _evidence(match: Match) -> Evidence:
    chunk = match.chunk
    return Evidence(
        evidence_id=f"ev-{chunk.chunk_key}",
        template_id=chunk.chunk_key,
        source_title=chunk.source_title,
        jurisdiction=chunk.jurisdiction,
        excerpt=chunk.text,
    )


async def _examples() -> npt.NDArray[np.float32]:
    global _example_vectors
    if _example_vectors is None:
        texts = [text for examples in TOPIC_EXAMPLES.values() for text in examples]
        _example_vectors = await embedder().embed(texts, "RETRIEVAL_QUERY")
    return _example_vectors


async def plan_clauses(texts: Sequence[str], contract_type: str | None) -> list[ClausePlan]:
    """Find evidence and a topic for every clause, with one embedding call for them all.

    Without a published corpus (local development) the synthetic templates stand in.
    If embedding fails, search falls back to exact words and topics stay unknown.
    """
    with tracer.start_as_current_span("mbiu.retrieve") as span:
        span.set_attribute("mbiu.stage", "retrieve")
        span.set_attribute("mbiu.clause_count", len(texts))
        # The first call reads the database, which Django forbids on the event loop
        snapshot = await asyncio.to_thread(active_snapshot)
        try:
            vectors: npt.NDArray[np.float32] | None = await embedder().embed(
                list(texts), "RETRIEVAL_QUERY"
            )
            examples: npt.NDArray[np.float32] | None = await _examples()
        except LLMError as err:
            logger.warning("Clause embedding failed (%s); using exact-word search", err)
            span.set_attribute("mbiu.embedding_failed", True)
            vectors = examples = None

        # A known contract type with no template of that type can't be compared fairly
        has_standard = (
            snapshot is None
            or contract_type is None
            or any(c.contract_type == contract_type for c in snapshot.chunks)
        )
        plans = []
        for i, text in enumerate(texts):
            vector = None if vectors is None else vectors[i]
            topic = (
                classify(vector, examples, _EXAMPLE_TOPICS)
                if vector is not None and examples is not None
                else None
            )
            if snapshot is None:
                plans.append(ClausePlan(retrieve_simple_evidence(text), topic))
            elif not has_standard:
                plans.append(ClausePlan([], topic, note=NO_STANDARD_NOTE))
            else:
                matches = search(
                    snapshot, text, vector, contract_type=contract_type, k=EVIDENCE_PER_CLAUSE
                )
                plans.append(ClausePlan([_evidence(m) for m in matches], topic))
        span.set_attribute("mbiu.corpus_loaded", snapshot is not None)
        return plans


async def corpus_version() -> str:
    """The version tag of the corpus results were compared with."""
    snapshot = await asyncio.to_thread(active_snapshot)
    return snapshot.version_tag if snapshot is not None else SYNTHETIC_CORPUS_VERSION
