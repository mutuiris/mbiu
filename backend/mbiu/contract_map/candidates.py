"""Candidate pair generation for whole-contract mapping.

Selects pairs of clauses to check for conflicts or overrides:
1. Every pair linked deterministically (cross-references, overrides, defined terms).
2. Same-topic clauses (clustered by functional topic: term/renewal, royalties/payment,
   rights/ownership, exclusivity, termination).

Ensures work scales linearly O(N) with contract length, avoiding O(N^2) combinatorial explosion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from mbiu.api.schemas import ClauseLink
from mbiu.documents.segment import Clause, SegmentedDocument

_TOPIC_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "term_renewal": re.compile(
        r"\b(?:term|duration|renewal|renew|extension|expires?|expiry|expiration"
        r"|period\s+of\s+(?:this\s+)?agreement|effective\s+date)\b",
        re.IGNORECASE,
    ),
    "royalties_payment": re.compile(
        r"\b(?:royalt(?:y|ies)|gross\s+receipts|net\s+receipts|payments?|statements?"
        r"|account(?:ing|s)?|audit|inspect\s+books|recoup(?:able|ment)?|deduct(?:ions?)?)\b",
        re.IGNORECASE,
    ),
    "rights_ownership": re.compile(
        r"\b(?:grant\s+of\s+rights|ownership|own\s+the|master\s+recordings?|compositions?"
        r"|copyright|licen[sc]e|exploit(?:ation)?|assign(?:ment)?)\b",
        re.IGNORECASE,
    ),
    "exclusivity": re.compile(
        r"\b(?:exclusiv(?:e|ely|ity)|non-exclusive|restrict(?:ion)?|compete|lockout)\b",
        re.IGNORECASE,
    ),
    "termination": re.compile(
        r"\b(?:terminat(?:e|ion)|material\s+breach|cure\s+period|default|insolven(?:cy|t))\b",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class CandidatePair:
    """A pair of clauses nominated for conflict or override evaluation."""

    clause_a: Clause
    clause_b: Clause
    reasons: tuple[str, ...]

    @property
    def clause_ids(self) -> tuple[str, str]:
        """Return the clause ID tuple for the candidate pair."""
        return (self.clause_a.clause_id, self.clause_b.clause_id)


def classify_clause_topics(clause: Clause) -> set[str]:
    """Identify which functional topics a clause touches."""
    topics: set[str] = set()
    text = (clause.title or "") + " " + clause.text
    for topic, pattern in _TOPIC_PATTERNS.items():
        if pattern.search(text):
            topics.add(topic)
    return topics


def build_candidate_pairs(
    segmented: SegmentedDocument,
    deterministic_links: list[ClauseLink],
) -> tuple[list[CandidatePair], list[ClauseLink]]:
    """Build candidate pairs for conflict/override inspection.

    Args:
        segmented: The segmented contract document.
        deterministic_links: Links discovered by deterministic rules.

    Returns:
        A tuple of (candidate pairs list, updated list of ClauseLinks including same_topic).
    """
    clause_map: dict[str, Clause] = {c.clause_id: c for c in segmented.clauses}
    pairs_dict: dict[tuple[str, str], list[str]] = {}
    same_topic_links: list[ClauseLink] = []

    # Helper to add a candidate pair
    def add_pair(id_a: str, id_b: str, reason: str) -> None:
        if id_a == id_b:
            return
        c_a = clause_map.get(id_a)
        c_b = clause_map.get(id_b)
        if not c_a or not c_b:
            return

        key = (id_a, id_b)
        if key not in pairs_dict and (id_b, id_a) in pairs_dict:
            pairs_dict[(id_b, id_a)].append(reason)
        else:
            pairs_dict.setdefault(key, []).append(reason)

    # 1. Every linked pair from deterministic links
    for link in deterministic_links:
        add_pair(link.from_clause_id, link.to_clause_id, f"link:{link.kind}")

    # 2. Same-topic clustering
    topic_clusters: dict[str, list[Clause]] = {}
    for clause in segmented.clauses:
        topics = classify_clause_topics(clause)
        for topic in topics:
            topic_clusters.setdefault(topic, []).append(clause)

    seen_same_topic: set[tuple[str, str]] = set()
    for topic, cluster in topic_clusters.items():
        # Pair within topic cluster (cluster sizes are naturally bounded, keeping O(N))
        for i in range(len(cluster)):
            for j in range(i + 1, min(len(cluster), i + 6)):
                c1 = cluster[i]
                c2 = cluster[j]
                add_pair(c1.clause_id, c2.clause_id, f"topic:{topic}")
                pair_key = (c1.clause_id, c2.clause_id)
                if pair_key not in seen_same_topic:
                    seen_same_topic.add(pair_key)
                    same_topic_links.append(
                        ClauseLink(
                            from_clause_id=c1.clause_id,
                            to_clause_id=c2.clause_id,
                            kind="same_topic",
                        )
                    )

    candidate_pairs: list[CandidatePair] = []
    for (id_a, id_b), reasons in pairs_dict.items():
        c_a = clause_map[id_a]
        c_b = clause_map[id_b]
        candidate_pairs.append(
            CandidatePair(
                clause_a=c_a,
                clause_b=c_b,
                reasons=tuple(reasons),
            )
        )

    # Merge deterministic links with unique same_topic links
    existing_pairs = {(item.from_clause_id, item.to_clause_id) for item in deterministic_links}
    all_links = list(deterministic_links)
    for st_link in same_topic_links:
        if (st_link.from_clause_id, st_link.to_clause_id) not in existing_pairs:
            all_links.append(st_link)

    return candidate_pairs, all_links
