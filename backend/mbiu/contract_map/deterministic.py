"""Deterministic link extraction for whole-contract mapping.

Extracts links between clauses purely through code without invoking an LLM:
1. Cross-references ("clause 12", "clause 2.1", "Schedule B", "Annex A")
2. Override wording ("notwithstanding", "subject to", "save as provided")
3. Defined terms map (links clauses using defined terms to the defining clause)

Enforces zero-storage invariants: operates purely in-memory on SegmentedDocument structures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from mbiu.api.schemas import ClauseLink
from mbiu.documents.segment import Clause, DefinedTerm, SegmentedDocument

# Patterns for explicit cross-references to clauses
_CROSS_REF_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:clauses?|sections?|paragraphs?|articles?)\s+"
    r"([0-9]+(?:\.[0-9]+)*(?:\([a-zA-Z0-9]+\))*)"
    r"(?:\s*(?:and|,|to)\s*([0-9]+(?:\.[0-9]+)*(?:\([a-zA-Z0-9]+\))*))?",
    re.IGNORECASE,
)

_SCHEDULE_REF_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:Schedule|Annex|Appendix|Exhibit)\s+([A-Z0-9]+(?:\.[0-9]+)*)\b",
    re.IGNORECASE,
)

# Override patterns targeting specific clauses
_OVERRIDE_CLAUSE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:"
    r"notwithstanding\s+(?:the\s+provisions\s+of\s+)?(?:clauses?|sections?)\s+([0-9]+(?:\.[0-9]+)*)"
    r"|subject\s+to\s+(?:the\s+provisions\s+of\s+)?(?:clauses?|sections?)\s+([0-9]+(?:\.[0-9]+)*)"
    r"|(?:save|except)\s+as\s+provided\s+(?:in|under)\s+(?:clauses?|sections?)\s+([0-9]+(?:\.[0-9]+)*)"
    r"|in\s+the\s+event\s+of\s+(?:any\s+)?conflict\s+(?:with|between)\s+(?:clauses?|sections?)\s+([0-9]+(?:\.[0-9]+)*)"
    r"|(?:shall\s+prevail\s+over|prevails\s+over)\s+(?:clauses?|sections?)\s+([0-9]+(?:\.[0-9]+)*)"
    r"|without\s+prejudice\s+to\s+(?:the\s+generality\s+of\s+)?(?:clauses?|sections?)\s+([0-9]+(?:\.[0-9]+)*)"
    r")\b",
    re.IGNORECASE,
)

# General override wording (even without naming a specific clause)
_GENERAL_OVERRIDE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:"
    r"notwithstanding\s+anything\s+to\s+the\s+contrary"
    r"|notwithstanding\s+the\s+foregoing"
    r"|in\s+the\s+event\s+of\s+(?:any\s+)?conflict\s+or\s+inconsistency"
    r"|shall\s+supersede\s+all\s+prior"
    r"|prevails?\s+in\s+the\s+event\s+of\s+(?:any\s+)?conflict"
    r")\b",
    re.IGNORECASE,
)

# Common generic legal terms to ignore when mapping defined term links to avoid noise
_GENERIC_DEFINED_TERMS: Final[set[str]] = {
    "agreement",
    "parties",
    "party",
    "person",
    "effective date",
    "applicable law",
    "business day",
    "calendar month",
    "hereof",
    "herein",
    "schedule",
    "annex",
}


@dataclass(frozen=True)
class OverrideOccurrence:
    """An override phrase detected in a clause, either targeted or general."""

    from_clause_id: str
    target_clause_id: str | None
    matched_phrase: str
    is_general: bool


def find_cross_references(clauses: list[Clause]) -> list[ClauseLink]:
    """Find explicit cross-references between clauses in the contract.

    Args:
        clauses: List of clauses in the segmented document.

    Returns:
        List of unique ClauseLink objects of kind 'cross_reference'.
    """
    valid_ids: set[str] = {c.clause_id for c in clauses}
    links: list[ClauseLink] = []
    seen: set[tuple[str, str, str]] = set()

    for clause in clauses:
        src = clause.clause_id

        # Search for "clause X" or "clauses X and Y"
        for match in _CROSS_REF_RE.finditer(clause.text):
            target_1 = match.group(1)
            target_2 = match.group(2)

            for target in (target_1, target_2):
                if not target:
                    continue
                # Normalize target clause ID: try exact, or without trailing periods
                clean_target = target.rstrip(".")
                if clean_target in valid_ids and clean_target != src:
                    key = (src, clean_target, "cross_reference")
                    if key not in seen:
                        seen.add(key)
                        links.append(
                            ClauseLink(
                                from_clause_id=src,
                                to_clause_id=clean_target,
                                kind="cross_reference",
                            )
                        )

        # Search for Schedule / Annex references
        for match in _SCHEDULE_REF_RE.finditer(clause.text):
            sched_name = match.group(0).strip()
            # Find any clause whose section or title matches the schedule
            for target_clause in clauses:
                if target_clause.clause_id == src:
                    continue
                if target_clause.section.lower() == sched_name.lower() or (
                    target_clause.title and sched_name.lower() in target_clause.title.lower()
                ):
                    key = (src, target_clause.clause_id, "cross_reference")
                    if key not in seen:
                        seen.add(key)
                        links.append(
                            ClauseLink(
                                from_clause_id=src,
                                to_clause_id=target_clause.clause_id,
                                kind="cross_reference",
                            )
                        )

    return links


def find_override_links(
    clauses: list[Clause],
) -> tuple[list[ClauseLink], list[OverrideOccurrence]]:
    """Detect override language ('notwithstanding', 'subject to', etc.) in clauses.

    Args:
        clauses: List of clauses in the segmented document.

    Returns:
        A tuple of (list of ClauseLink with kind='override', list of OverrideOccurrence records).
    """
    valid_ids: set[str] = {c.clause_id for c in clauses}
    links: list[ClauseLink] = []
    occurrences: list[OverrideOccurrence] = []
    seen: set[tuple[str, str, str]] = set()

    for clause in clauses:
        src = clause.clause_id

        # 1. Targeted overrides (mentions specific clause)
        for match in _OVERRIDE_CLAUSE_RE.finditer(clause.text):
            matched_phrase = match.group(0)
            # Find the non-None captured clause ID
            target_id = next((g for g in match.groups() if g is not None), None)
            if target_id:
                clean_target = target_id.rstrip(".")
                if clean_target in valid_ids and clean_target != src:
                    occurrences.append(
                        OverrideOccurrence(
                            from_clause_id=src,
                            target_clause_id=clean_target,
                            matched_phrase=matched_phrase,
                            is_general=False,
                        )
                    )
                    key = (src, clean_target, "override")
                    if key not in seen:
                        seen.add(key)
                        links.append(
                            ClauseLink(
                                from_clause_id=src,
                                to_clause_id=clean_target,
                                kind="override",
                            )
                        )

        # 2. General override wording ("notwithstanding anything to the contrary", etc.)
        for match in _GENERAL_OVERRIDE_RE.finditer(clause.text):
            occurrences.append(
                OverrideOccurrence(
                    from_clause_id=src,
                    target_clause_id=None,
                    matched_phrase=match.group(0),
                    is_general=True,
                )
            )

    return links, occurrences


def find_defined_term_links(
    clauses: list[Clause],
    defined_terms: list[DefinedTerm],
) -> list[ClauseLink]:
    """Map clauses using a defined term to the clause where that term is defined.

    Args:
        clauses: List of clauses in the segmented document.
        defined_terms: Detailed defined terms extracted by the clause splitter.

    Returns:
        List of ClauseLink objects with kind='defined_term'.
    """
    links: list[ClauseLink] = []
    seen: set[tuple[str, str, str]] = set()

    # Build mapping from normalized term to defining clause
    terms_map: dict[str, str] = {}
    for dt in defined_terms:
        clean_term = dt.term.strip("\"'“”‘’").strip()
        if len(clean_term) >= 3 and clean_term.lower() not in _GENERIC_DEFINED_TERMS:
            terms_map[clean_term] = dt.clause_id

    if not terms_map:
        return links

    # Search for each term in clauses other than the defining clause
    for term, def_clause_id in terms_map.items():
        pattern = re.compile(rf"\b{re.escape(term)}\b")
        for clause in clauses:
            if clause.clause_id == def_clause_id:
                continue
            if pattern.search(clause.text):
                key = (clause.clause_id, def_clause_id, "defined_term")
                if key not in seen:
                    seen.add(key)
                    links.append(
                        ClauseLink(
                            from_clause_id=clause.clause_id,
                            to_clause_id=def_clause_id,
                            kind="defined_term",
                        )
                    )

    return links


def build_deterministic_links(
    segmented: SegmentedDocument,
) -> tuple[list[ClauseLink], list[OverrideOccurrence]]:
    """Build all deterministic links and override occurrences from a SegmentedDocument.

    Args:
        segmented: The segmented contract representation.

    Returns:
        Tuple of (combined unique ClauseLinks, list of OverrideOccurrences).
    """
    cross_links = find_cross_references(segmented.clauses)
    override_links, occurrences = find_override_links(segmented.clauses)
    defined_term_links = find_defined_term_links(
        segmented.clauses, segmented.defined_terms_detailed
    )

    # Priority: override > cross_reference > defined_term
    # An override from A to B is also a cross-reference; suppress redundant cross-refs.
    override_pairs: set[tuple[str, str]] = {
        (item.from_clause_id, item.to_clause_id) for item in override_links
    }

    seen: set[tuple[str, str, str]] = set()
    combined: list[ClauseLink] = []

    for link in override_links:
        key = (link.from_clause_id, link.to_clause_id, link.kind)
        if key not in seen:
            seen.add(key)
            combined.append(link)

    for link in cross_links:
        pair = (link.from_clause_id, link.to_clause_id)
        if pair in override_pairs:
            continue
        key = (link.from_clause_id, link.to_clause_id, link.kind)
        if key not in seen:
            seen.add(key)
            combined.append(link)

    for link in defined_term_links:
        key = (link.from_clause_id, link.to_clause_id, link.kind)
        if key not in seen:
            seen.add(key)
            combined.append(link)

    return combined, occurrences
