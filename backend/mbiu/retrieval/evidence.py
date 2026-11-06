"""For each contract clause: the template evidence to compare with, and its topic."""

import asyncio
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt
from opentelemetry import trace

from mbiu.api.schemas import Evidence, MissingProtection
from mbiu.corpus.loader import active_snapshot
from mbiu.corpus.snapshot import CorpusSnapshot, SnapshotChunk
from mbiu.corpus.synthetic import retrieve_simple_evidence
from mbiu.evaluation.verify import NUMBER_WORDS
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

# Protections a standard template gives the artist, with a fixed, reviewed question for each
PROTECTIONS: Final[dict[str, str]] = {
    "accounting_audit": "Can we add a clause that lets me check your accounts once a year?",
    "termination": "Can we add a way for me to end this agreement if you break its terms?",
    "payment": "Can we write down when and how often I will be paid?",
}

_UNITS: Final = {"day": "days", "month": "months", "year": "years", "%": "%", "per cent": "%"}
_number = r"\d+(?:\.\d+)?|" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
_FIGURE: Final = re.compile(
    rf"\b({_number})\s*(%|per\s?cent|days?|months?|years?)\b", re.IGNORECASE
)

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
    # Shown on the card but doesn't change the verdict, e.g. templates that disagree
    context: str | None = None


def _figures(text: str) -> dict[str, set[float]]:
    """Durations and percentages in a text, by unit."""
    found: dict[str, set[float]] = {}
    for number, unit in _FIGURE.findall(text):
        value = float(NUMBER_WORDS.get(number.lower(), number))
        key = unit.lower().replace("per cent", "%").replace("percent", "%").rstrip("s")
        found.setdefault(_UNITS.get(key, key), set()).add(value)
    return found


def _show(value: float, unit: str) -> str:
    number = f"{value:g}"
    return f"{number}%" if unit == "%" else f"{number} {unit}"


def disagreement(clause: str, templates: Sequence[SnapshotChunk]) -> str | None:
    """Say so when two templates give different figures for something the clause also sets."""
    if len(templates) < 2:
        return None
    first, second, mine = _figures(templates[0].text), _figures(templates[1].text), _figures(clause)
    for unit in ("days", "months", "years", "%"):
        a, b, c = first.get(unit), second.get(unit), mine.get(unit)
        if a and b and c and len(a) == len(b) == len(c) == 1 and a != b:
            return (
                f"Standard templates differ here: one gives {_show(min(a), unit)}, "
                f"another {_show(min(b), unit)}. Your contract gives {_show(min(c), unit)}."
            )
    return None


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
                # Two matches: the best is sent to the model, the second shows disagreement
                matches = search(snapshot, text, vector, contract_type=contract_type, k=2)
                plans.append(
                    ClausePlan(
                        [_evidence(m) for m in matches[:EVIDENCE_PER_CLAUSE]],
                        topic,
                        context=disagreement(text, [m.chunk for m in matches]),
                    )
                )
        span.set_attribute("mbiu.corpus_loaded", snapshot is not None)
        return plans


async def corpus_version() -> str:
    """The version tag of the corpus results were compared with."""
    snapshot = await asyncio.to_thread(active_snapshot)
    return snapshot.version_tag if snapshot is not None else SYNTHETIC_CORPUS_VERSION


def _missing(
    snapshot: CorpusSnapshot, topics: Sequence[str | None], contract_type: str | None
) -> list[MissingProtection]:
    present = {t for t in topics if t is not None}
    missing = []
    for topic, question in PROTECTIONS.items():
        if topic in present:
            continue
        templates = sorted(
            (
                c
                for c in snapshot.chunks
                if c.topic == topic and contract_type in (None, c.contract_type)
            ),
            key=lambda c: c.jurisdiction != "KE",
        )
        if templates:
            chunk = templates[0]
            missing.append(
                MissingProtection(
                    template_id=chunk.chunk_key,
                    title=chunk.title or topic.replace("_", " ").capitalize(),
                    excerpt=chunk.text,
                    ask_them=question,
                )
            )
    return missing


async def missing_protections(
    topics: Sequence[str | None], contract_type: str | None
) -> list[MissingProtection]:
    """Protections the matching standard has that no clause in the contract covers.

    Needs a published corpus and known topics; without either it can't tell, so says nothing.
    """
    snapshot = await asyncio.to_thread(active_snapshot)
    if snapshot is None or all(t is None for t in topics):
        return []
    return _missing(snapshot, topics, contract_type)
