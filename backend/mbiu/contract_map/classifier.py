"""Contract type classification for whole-contract mapping (MB-14).

Identifies the contract type against reviewed standard templates:
- 'recording'
- 'publishing'
- 'management'
- 'distribution'
- 'live_performance'
- None (when no reviewed standard covers the contract)
"""

from __future__ import annotations

import re
from typing import Final

from mbiu.documents.segment import SegmentedDocument

_RECORDING_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:recording\s+agreement|record\s+company|master\s+recordings?|exclusive\s+recording"
    r"|artist\s+recording|record\s+label|phonorecord|studio\s+recordings?)\b",
    re.IGNORECASE,
)

_PUBLISHING_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:music\s+publishing|publishing\s+agreement|songwriter\s+agreement|musical\s+works?"
    r"|musical\s+compositions?|print\s+rights|mechanical\s+royalties|synchronization\s+rights)\b",
    re.IGNORECASE,
)

_MANAGEMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:artist\s+management|management\s+agreement|personal\s+manager|manager\s+commission"
    r"|artist\s+career\s+guidance|booking\s+agent)\b",
    re.IGNORECASE,
)

_DISTRIBUTION_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:digital\s+distribution|distribution\s+agreement|digital\s+streaming\s+platforms?"
    r"|dsp\s+distribution|digital\s+aggregator|physical\s+distribution)\b",
    re.IGNORECASE,
)

_LIVE_PERFORMANCE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:live\s+performance|performance\s+agreement|gig\s+agreement|concert\s+engagement"
    r"|venue\s+engagement|sound\s+check|stage\s+performance)\b",
    re.IGNORECASE,
)


def detect_contract_type(segmented: SegmentedDocument) -> str | None:
    """Classify the contract type based on document text and structural cues.

    Args:
        segmented: The segmented contract document.

    Returns:
        One of 'recording', 'publishing', 'management', 'distribution',
        'live_performance', or None if no reviewed standard matches.
    """
    # Sample up to the first 10 clauses or recitals/preamble where contract title/purpose resides
    header_texts: list[str] = []
    for clause in segmented.clauses[:10]:
        if clause.title:
            header_texts.append(clause.title)
        header_texts.append(clause.text[:300])

    combined_header = " ".join(header_texts)

    # Priority scoring based on matches in preamble and title
    scores: dict[str, int] = {
        "recording": len(_RECORDING_RE.findall(combined_header)),
        "publishing": len(_PUBLISHING_RE.findall(combined_header)),
        "management": len(_MANAGEMENT_RE.findall(combined_header)),
        "distribution": len(_DISTRIBUTION_RE.findall(combined_header)),
        "live_performance": len(_LIVE_PERFORMANCE_RE.findall(combined_header)),
    }

    # If header was inconclusive, check full contract text
    if max(scores.values()) == 0:
        full_sample = " ".join(c.text for c in segmented.clauses)
        scores["recording"] = len(_RECORDING_RE.findall(full_sample))
        scores["publishing"] = len(_PUBLISHING_RE.findall(full_sample))
        scores["management"] = len(_MANAGEMENT_RE.findall(full_sample))
        scores["distribution"] = len(_DISTRIBUTION_RE.findall(full_sample))
        scores["live_performance"] = len(_LIVE_PERFORMANCE_RE.findall(full_sample))

    best_type, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_type

    return None
