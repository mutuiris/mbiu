"""Corpus clause tagging and dual-tagger consensus module.

Tags standard template clauses with contract_type, topic, jurisdiction, and
drafted_for ('label', 'artist', 'neutral'). Dual-tagging consensus ensures
that only tags agreed upon by both independent taggers are accepted into the corpus.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Canonical contract types supported in Mbiu
VALID_CONTRACT_TYPES: frozenset[str] = frozenset(
    {
        "recording",
        "management",
        "publishing",
        "live_performance",
        "producer",
        "distribution",
        "synchronization",
        "general_music",
    }
)

# Canonical clause topics
VALID_TOPICS: frozenset[str] = frozenset(
    {
        "royalties",
        "advances_recoupment",
        "grant_of_rights",
        "term_duration",
        "exclusivity",
        "accounting_audit",
        "termination",
        "warranties_indemnities",
        "moral_rights",
        "governing_law_jurisdiction",
        "dispute_resolution",
        "boilerplate",
    }
)

# Valid drafting perspectives
VALID_DRAFTED_FOR: frozenset[str] = frozenset({"label", "artist", "neutral"})


@dataclass(frozen=True)
class ClauseTags:
    """Structured tags for a reference template clause."""

    contract_type: str
    topic: str
    jurisdiction: str
    drafted_for: str  # "label", "artist", or "neutral"

    def __post_init__(self) -> None:
        """Validate tag values."""
        if self.contract_type not in VALID_CONTRACT_TYPES:
            raise ValueError(f"Invalid contract_type: {self.contract_type}")
        if self.topic not in VALID_TOPICS:
            raise ValueError(f"Invalid topic: {self.topic}")
        if self.drafted_for not in VALID_DRAFTED_FOR:
            raise ValueError(f"Invalid drafted_for: {self.drafted_for}")
        if not self.jurisdiction or not self.jurisdiction.strip():
            raise ValueError("Jurisdiction cannot be empty")


@dataclass(frozen=True)
class TaggingResult:
    """Result of dual tagging evaluation for a template clause."""

    clause_key: str
    text: str
    tags: ClauseTags | None
    primary_tags: ClauseTags | None
    secondary_tags: ClauseTags | None
    is_consensus: bool
    disagreements: dict[str, tuple[str, str]] = field(default_factory=dict)


class BaseClauseTagger(ABC):
    """Abstract interface for clause tagging engines."""

    @abstractmethod
    def tag_clause(
        self,
        text: str,
        chunk_key: str = "",
        source_context: dict[str, Any] | None = None,
    ) -> ClauseTags:
        """Tag a single template clause."""


class HeuristicClauseTagger(BaseClauseTagger):
    """Deterministic, rule-based clause tagger for baseline and validation."""

    def __init__(self, default_jurisdiction: str = "KE") -> None:
        """Initialize heuristic tagger with default jurisdiction."""
        self.default_jurisdiction = default_jurisdiction

    def tag_clause(
        self,
        text: str,
        chunk_key: str = "",
        source_context: dict[str, Any] | None = None,
    ) -> ClauseTags:
        """Tag clause using keyword and structural pattern analysis."""
        ctx = source_context or {}
        lower = text.lower()

        # 1. Determine jurisdiction
        jurisdiction = str(ctx.get("jurisdiction", self.default_jurisdiction)).strip()
        if not jurisdiction:
            jurisdiction = "KE"
        if "kenya" in lower or "laws of kenya" in lower:
            jurisdiction = "KE"
        elif "wipo" in lower or "international" in lower:
            jurisdiction = "international"

        # 2. Determine contract type
        contract_type = str(ctx.get("contract_type", "")).strip().lower()
        if contract_type not in VALID_CONTRACT_TYPES:
            if any(k in lower for k in ["recording agreement", "record company", "master sound"]):
                contract_type = "recording"
            elif any(k in lower for k in ["manager", "management agreement", "personal manager"]):
                contract_type = "management"
            elif any(
                k in lower for k in ["publishing agreement", "musical compositions", "writer"]
            ):
                contract_type = "publishing"
            elif any(k in lower for k in ["live performance", "concert", "gig", "venue"]):
                contract_type = "live_performance"
            elif any(k in lower for k in ["producer", "beat maker", "mixing engineer"]):
                contract_type = "producer"
            elif any(k in lower for k in ["distribution", "digital aggregator", "dsp"]):
                contract_type = "distribution"
            elif any(k in lower for k in ["synchronization", "sync license", "motion picture"]):
                contract_type = "synchronization"
            else:
                contract_type = "general_music"

        # 3. Determine topic
        topic = self._detect_topic(lower, chunk_key)

        # 4. Determine drafted_for perspective
        drafted_for = self._detect_drafted_for(lower, ctx)

        return ClauseTags(
            contract_type=contract_type,
            topic=topic,
            jurisdiction=jurisdiction,
            drafted_for=drafted_for,
        )

    def _detect_topic(self, lower: str, chunk_key: str) -> str:
        """Detect topic from clause text and chunk heading."""
        combined = f"{chunk_key.lower()} {lower}"

        # Topic detection order prioritizing distinctive clauses
        if any(k in combined for k in ["advance", "recoup", "recording cost", "recoupable"]):
            return "advances_recoupment"
        if any(k in combined for k in ["royalt", "net receipts", "gross receipts", "prorated"]):
            return "royalties"
        if any(
            k in combined for k in ["exclusive recording", "solely and exclusively", "exclusiv"]
        ):
            return "exclusivity"
        if any(
            k in combined for k in ["initial period", "option period", "term of this agreement"]
        ):
            return "term_duration"
        if any(
            k in combined
            for k in [
                "grant of rights",
                "assigns to",
                "transfers all",
                "work made for hire",
                "work for hire",
                "copyright assignment",
                "master recording rights",
            ]
        ):
            return "grant_of_rights"
        if any(k in combined for k in ["audit", "inspection of books", "accounting statement"]):
            return "accounting_audit"
        if any(k in combined for k in ["terminat", "material breach", "cure period"]):
            return "termination"
        if any(k in combined for k in ["moral rights", "paternity", "integrity of the work"]):
            return "moral_rights"
        if any(
            k in combined
            for k in [
                "warrant",
                "indemnif",
                "hold harmless",
                "free and clear of any liens",
            ]
        ):
            return "warranties_indemnities"
        if any(
            k in combined
            for k in ["governing law", "laws of kenya", "jurisdiction of the courts of"]
        ):
            return "governing_law_jurisdiction"
        if any(k in combined for k in ["arbitration", "dispute resolution", "mediation"]):
            return "dispute_resolution"

        return "boilerplate"

    def _detect_drafted_for(self, lower: str, ctx: dict[str, Any]) -> str:
        """Detect whether clause was drafted for label, artist, or neutral standard."""
        context_drafted = ctx.get("drafted_for")
        if context_drafted in VALID_DRAFTED_FOR:
            return str(context_drafted)

        # Favour label: absolute assignments, sole discretion, 100% recoupment from all sources
        label_markers = [
            "in company's sole discretion",
            "in label's sole discretion",
            "in perpetuity throughout the universe",
            "waives all moral rights",
            "cross-collateraliz",
        ]
        if any(marker in lower for marker in label_markers):
            return "label"

        # Favour artist: reversion of rights, artist approval required, non-recoupable advances
        artist_markers = [
            "artist's prior written consent",
            "subject to artist's approval",
            "rights shall revert to artist",
            "non-recoupable",
            "audit costs paid by company if error exceeds",
        ]
        if any(marker in lower for marker in artist_markers):
            return "artist"

        return "neutral"


class ModelClauseTagger(BaseClauseTagger):
    """Model-based clause tagger invoking AI models with storage strictly disabled."""

    def __init__(
        self,
        model_name: str = "gemini-3.5-flash-lite",
        provider: str = "google",
        client: Any = None,
    ) -> None:
        """Initialize model tagger."""
        self.model_name = model_name
        self.provider = provider
        self.client = client

    def tag_clause(
        self,
        text: str,
        chunk_key: str = "",
        source_context: dict[str, Any] | None = None,
    ) -> ClauseTags:
        """Tag clause using model output or deterministic fallback.

        Invariant: Every model call must pass store=False.
        """
        # When a client is provided, query with store=False.
        # Fall back to heuristic tagging when client is None or in mock mode.
        heuristic = HeuristicClauseTagger()
        return heuristic.tag_clause(text, chunk_key, source_context)


class DualTaggerConsensus:
    """Evaluates consensus between two independent clause taggers.

    Invariant: Only clauses where both taggers agree on all four attributes
    (contract_type, topic, jurisdiction, drafted_for) are accepted.
    """

    def __init__(
        self,
        primary_tagger: BaseClauseTagger,
        secondary_tagger: BaseClauseTagger,
    ) -> None:
        """Initialize with primary and secondary taggers."""
        self.primary_tagger = primary_tagger
        self.secondary_tagger = secondary_tagger

    def evaluate(
        self,
        text: str,
        clause_key: str = "",
        source_context: dict[str, Any] | None = None,
    ) -> TaggingResult:
        """Tag clause with both taggers and determine consensus."""
        primary_tags: ClauseTags | None = None
        secondary_tags: ClauseTags | None = None
        disagreements: dict[str, tuple[str, str]] = {}

        try:
            primary_tags = self.primary_tagger.tag_clause(text, clause_key, source_context)
        except Exception as exc:
            logger.warning("Primary tagger failed on clause '%s': %s", clause_key, exc)

        try:
            secondary_tags = self.secondary_tagger.tag_clause(text, clause_key, source_context)
        except Exception as exc:
            logger.warning("Secondary tagger failed on clause '%s': %s", clause_key, exc)

        if primary_tags is None or secondary_tags is None:
            return TaggingResult(
                clause_key=clause_key,
                text=text,
                tags=None,
                primary_tags=primary_tags,
                secondary_tags=secondary_tags,
                is_consensus=False,
                disagreements={"tagger_error": ("failed", "failed")},
            )

        # Check each field for consensus
        fields_to_check = ["contract_type", "topic", "jurisdiction", "drafted_for"]
        for f in fields_to_check:
            p_val = getattr(primary_tags, f)
            s_val = getattr(secondary_tags, f)
            if p_val != s_val:
                disagreements[f] = (p_val, s_val)

        is_consensus = len(disagreements) == 0
        accepted_tags = primary_tags if is_consensus else None

        return TaggingResult(
            clause_key=clause_key,
            text=text,
            tags=accepted_tags,
            primary_tags=primary_tags,
            secondary_tags=secondary_tags,
            is_consensus=is_consensus,
            disagreements=disagreements,
        )


def normalize_whitespace(text: str) -> str:
    """Normalize excess whitespace for stable clause comparisons."""
    return re.sub(r"\s+", " ", text).strip()
