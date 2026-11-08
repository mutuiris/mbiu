"""Synthetic reference corpus and legal-expert annotated exemplars for evaluation.

Provides hand-crafted standard templates derived from public guidelines
(WIPO, Kenya Copyright Act Cap. 130, Performers Protection Act Cap. 229A,
Income Tax Act Cap. 470, Data Protection Act 2019, and KECOBO guidance),
plus cached in-memory lookup of verified legal-expert annotated contract
exemplars from ``corpus/system_annotated_contracts/``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Final

from mbiu.api.schemas import Evidence

_WORD_RE: Final = re.compile(r"[a-z0-9]{3,}")
_STOPWORDS: Final = frozenset(
    {
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "from",
        "shall",
        "any",
        "all",
        "not",
        "are",
        "was",
        "were",
        "will",
        "may",
        "can",
        "such",
        "under",
        "into",
        "upon",
        "have",
        "has",
        "had",
        "its",
        "their",
        "other",
        "which",
        "agreement",
        "party",
        "parties",
        "clause",
    }
)
_ANNOTATED_JSONL_PATH: Final = (
    Path(__file__).resolve().parents[3]
    / "corpus"
    / "system_annotated_contracts"
    / "mbiu_context_and_finetuning_dataset.jsonl"
)


@dataclass(frozen=True)
class SyntheticTemplateClause:
    """A single synthetic reference template clause."""

    template_id: str
    source_title: str
    jurisdiction: str
    topic: str
    excerpt: str
    keywords: tuple[str, ...]

    def to_evidence(self, evidence_id: str) -> Evidence:
        """Convert to an API Evidence model."""
        return Evidence(
            evidence_id=evidence_id,
            template_id=self.template_id,
            source_title=self.source_title,
            jurisdiction=self.jurisdiction,
            excerpt=self.excerpt,
        )


@dataclass(frozen=True)
class AnnotatedExemplar:
    """In-memory legal-expert annotated clause exemplar for few-shot prompt context."""

    document_id: str
    contract_type: str
    clause_id: str
    topic: str
    comparison_outcome: str
    clause_text: str
    reference_standard_id: str
    reference_standard_text: str
    headline: str
    what_it_says: str
    what_it_means: str
    ask_them: str | None
    keywords: frozenset[str]

    def format_for_prompt(self) -> str:
        """Format the verified legal-expert annotation as a compact few-shot reference."""
        ask_line = f"\nask_them: {self.ask_them}" if self.ask_them else ""
        return (
            f"Sample Clause ({self.contract_type}): {self.clause_text}\n"
            f"Reference Standard ({self.reference_standard_id}): {self.reference_standard_text}\n"
            f"Verified Evaluation:\n"
            f"comparison: {self.comparison_outcome}\n"
            f"headline: {self.headline}\n"
            f"what_it_says: {self.what_it_says}\n"
            f"what_it_means: {self.what_it_means}"
            f"{ask_line}"
        )


SYNTHETIC_CORPUS: Final[tuple[SyntheticTemplateClause, ...]] = (
    SyntheticTemplateClause(
        template_id="tpl-wipo-recording-royalties",
        source_title="WIPO Guide on Music Contracts (Model Agreement)",
        jurisdiction="KE / International",
        topic="royalties",
        excerpt=(
            "The Label shall pay to the Artist a royalty of not less than 15% to 20% "
            "of Gross Receipts derived from the commercial exploitation of the Masters, "
            "calculated without deduction of marketing, distribution overhead, "
            "or administrative costs."
        ),
        keywords=("royalty", "royalties", "receipts", "gross", "net", "sales", "streaming", "%"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-recoupment",
        source_title="KECOBO Standard Guidance on Recording Deals",
        jurisdiction="KE",
        topic="recoupment",
        excerpt=(
            "Direct recording and production costs approved in advance in writing shall be "
            "recoupable solely from the Artist's accrued royalties. In no event shall the Artist "
            "be personally liable to repay unrecouped balances, nor shall income from live gigs "
            "or outside work be garnished for recoupment."
        ),
        keywords=("recoup", "recoupable", "recoupment", "advance", "costs", "studio", "expenses"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-wipo-term-duration",
        source_title="WIPO Guide on Music Contracts (Model Agreement)",
        jurisdiction="KE / International",
        topic="term",
        excerpt=(
            "The initial term of this Agreement shall be for a period of one (1) year "
            "from the Effective Date. Any extension or renewal options shall be exercisable "
            "only upon the mutual written agreement of both parties."
        ),
        keywords=("term", "duration", "period", "years", "months", "renewal", "extension"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap130-grant-of-rights",
        source_title="Kenya Copyright Act (Cap. 130) Standard Assignment Provisions",
        jurisdiction="KE",
        topic="rights",
        excerpt=(
            "The Artist grants to the Company a non-exclusive license to reproduce and "
            "distribute the Masters for the duration of the agreed Term. All underlying "
            "copyrights, songwriting publishing shares, and moral rights remain strictly "
            "vested in the Artist."
        ),
        keywords=(
            "grant",
            "rights",
            "copyright",
            "masters",
            "ownership",
            "perpetual",
            "exclusive",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-exclusivity",
        source_title="KECOBO Guidelines on Artist Exclusivity",
        jurisdiction="KE",
        topic="exclusivity",
        excerpt=(
            "Exclusivity shall apply solely to the release of contracted studio recordings. "
            "The Artist retains full freedom to perform live, collaborate on non-competing "
            "projects, and pursue independent brand or freelance opportunities."
        ),
        keywords=(
            "exclusivity",
            "exclusive",
            "solely",
            "restrict",
            "perform",
            "freedom",
            "collaborate",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-wipo-accounting-audit",
        source_title="WIPO Guide on Music Contracts (Model Agreement)",
        jurisdiction="KE / International",
        topic="accounting",
        excerpt=(
            "The Company shall render detailed accounting statements semi-annually within sixty "
            "(60) days following 30 June and 31 December. The Artist shall have the right upon "
            "reasonable notice to inspect and audit all books, statements, and streaming logs "
            "relating to their works."
        ),
        keywords=(
            "accounting",
            "audit",
            "statements",
            "semi-annually",
            "quarterly",
            "inspect",
            "books",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-live-gig-compensation",
        source_title="Kenyan Live Performance Standard Terms",
        jurisdiction="KE",
        topic="compensation",
        excerpt=(
            "The Promoter shall pay the Artist a guaranteed fee with a minimum 50% "
            "non-refundable deposit payable upon execution, and the remaining balance "
            "immediately prior to or upon conclusion of the performance. Local hospitality "
            "and technical rider items shall be provided."
        ),
        keywords=("live", "gig", "performance", "promoter", "fee", "deposit", "venue", "rider"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-termination",
        source_title="KECOBO Model Artist Agreement",
        jurisdiction="KE",
        topic="termination",
        excerpt=(
            "Either party may terminate this Agreement upon thirty (30) days written notice for "
            "material breach, provided the breaching party fails to cure such breach within the "
            "thirty (30) day notice period."
        ),
        keywords=("terminate", "termination", "breach", "notice", "cure", "cancel"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-sync-endorsement",
        source_title=(
            "KECOBO Standard Synchronization & Brand Endorsement Guidelines / "
            "Kenya Data Protection Act (2019)"
        ),
        jurisdiction="KE",
        topic="rights",
        excerpt=(
            "Brand endorsement and synchronization licenses shall be strictly limited to the "
            "agreed Campaign Term, Territory, and specified media channels. The Artist retains "
            "100% copyright ownership of all musical works, and any artificial intelligence (AI) "
            "voice cloning or biometric likeness synthesis is prohibited without separate written "
            "consent under the Kenya Data Protection Act, 2019."
        ),
        keywords=(
            "endorsement",
            "ambassador",
            "campaign",
            "synchronization",
            "likeness",
            "biometric",
            "cloning",
            "brand",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap130-moral-rights-reversion",
        source_title="Kenya Copyright Act (Cap. 130, Sections 32 & 33) — Moral Rights & Assignment",
        jurisdiction="KE",
        topic="rights",
        excerpt=(
            "Under Section 32 of the Kenya Copyright Act (Cap. 130), the author's moral rights "
            "to claim authorship (paternity) and object to derogatory distortion (integrity) are "
            "inalienable during the author's lifetime. Under Section 33, any assignment must be "
            "in writing and unexploited works should revert to the Artist upon written notice."
        ),
        keywords=(
            "moral",
            "paternity",
            "integrity",
            "reversion",
            "revert",
            "section 32",
            "section 33",
            "unreleased",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap130-cmos-direct-share",
        source_title="Kenya Copyright Act (Cap. 130, Sec. 30A) & CISAC Writer's Share Rules",
        jurisdiction="KE / International",
        topic="royalties",
        excerpt=(
            "In any co-publishing or administration agreement, at least 50% of all public "
            "performance and broadcast royalties (the Writer's Share) shall be paid directly "
            "to the Songwriter by KECOBO-licensed CMOs (such as KAMP, PRISK, or PAVRISK) and "
            "shall never be assigned to or recouped by the Publisher."
        ),
        keywords=(
            "publishing",
            "publisher",
            "songwriter",
            "cmo",
            "pavrisk",
            "prisk",
            "kamp",
            "cisac",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap229a-performers-rights",
        source_title="Performers Protection Act (Cap. 229A, Laws of Kenya)",
        jurisdiction="KE",
        topic="rights",
        excerpt=(
            "Under the Performers Protection Act (Cap. 229A), no person shall broadcast, "
            "record, or make a commercial fixation of a Performer's live performance without "
            "the Performer's express written consent and separate equitable remuneration."
        ),
        keywords=("fixation", "broadcast", "livestream", "filming", "performer", "229a"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-wipo-management-sunset",
        source_title="WIPO & Music Managers Forum (MMF) Standard Management Agreement",
        jurisdiction="KE / International",
        topic="compensation",
        excerpt=(
            "The Manager's commission shall be 15% to 20% of Net Artist Earnings after deducting "
            "third-party touring, sound, and recording costs. All Artist funds shall be held in a "
            "separate trust account, and post-term sunset commissions shall step down to 10% in "
            "Year 1 and 5% in Year 2 before expiring completely."
        ),
        keywords=(
            "manager",
            "management",
            "commission",
            "sunset",
            "trust",
            "power of attorney",
            "fiduciary",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-producer-splits",
        source_title="KECOBO Standard Recording-Producer Agreement & Split-Sheet",
        jurisdiction="KE",
        topic="rights",
        excerpt=(
            "Where a Studio Producer contributes original musical composition (the Beat), the "
            "Producer and Artist shall execute a written Split Sheet recognizing the Producer's "
            "50% underlying composition share alongside a 3% to 4% PPD producer royalty on the "
            "master sound recording."
        ),
        keywords=("producer", "beat", "split", "stems", "trackouts", "instrumental", "ppd"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-digital-skiza-distribution",
        source_title="KECOBO Digital Aggregator & Skiza Ringback Distribution Standard",
        jurisdiction="KE",
        topic="royalties",
        excerpt=(
            "Under a standard digital distribution and Skiza ringback tune agreement, the Artist "
            "retains 100% ownership of the Masters and ISRC codes, receives 80% to 85% of net "
            "platform receipts, and may issue a 30-day takedown notice upon termination."
        ),
        keywords=("aggregator", "skiza", "ringback", "dsp", "takedown", "isrc", "ussd"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kra-cap470-withholding-tax",
        source_title="Kenya Income Tax Act (Cap. 470, Sec. 35) — Withholding Tax Standard",
        jurisdiction="KE",
        topic="payment",
        excerpt=(
            "Where statutory resident Withholding Tax (5% on professional/performance fees or "
            "royalties under the Kenya Income Tax Act, Cap. 470) is deducted, the payer shall "
            "remit the tax to the Kenya Revenue Authority (KRA) and furnish the official iTax "
            "Withholding Tax Certificate to the Artist within thirty (30) days."
        ),
        keywords=("withholding", "kra", "itax", "tax", "cap. 470", "pin", "vat"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-ncia-mediation-disputes",
        source_title="KECOBO & Nairobi Centre for International Arbitration (NCIA) Dispute Clause",
        jurisdiction="KE",
        topic="boilerplate",
        excerpt=(
            "This Agreement shall be governed by the laws of Kenya. Any dispute shall first be "
            "referred to good-faith mediation in Nairobi before KECOBO or the Nairobi Centre for "
            "International Arbitration (NCIA) prior to litigation in the Courts of Kenya."
        ),
        keywords=(
            "arbitration",
            "mediation",
            "ncia",
            "dispute",
            "governing",
            "jurisdiction",
            "courts",
        ),
    ),
)


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS)


@cache
def load_annotated_exemplars() -> tuple[AnnotatedExemplar, ...]:
    """Load and cache verified legal-expert annotated exemplars in memory once."""
    if not _ANNOTATED_JSONL_PATH.exists():
        return ()

    exemplars: list[AnnotatedExemplar] = []
    try:
        raw_lines = _ANNOTATED_JSONL_PATH.read_text(encoding="utf-8").splitlines()
        for line in raw_lines:
            if not line.strip():
                continue
            item: dict[str, Any] = json.loads(line)
            card = item.get("verified_mbiu_card", {})
            tags = item.get("expert_tags", {})
            ref_std = item.get("reference_standard", {})
            asks = card.get("ask_them", [])
            ask_str = asks[0] if isinstance(asks, list) and asks else None
            clause_text = str(item.get("clause_text", ""))
            topic = str(tags.get("topic", ""))
            exemplars.append(
                AnnotatedExemplar(
                    document_id=str(item.get("document_id", "")),
                    contract_type=str(item.get("contract_type", "")),
                    clause_id=str(item.get("clause_id", "")),
                    topic=topic,
                    comparison_outcome=str(tags.get("comparison_outcome", "worse_for_you")),
                    clause_text=clause_text,
                    reference_standard_id=str(ref_std.get("chunk_id", "")),
                    reference_standard_text=str(ref_std.get("text", "")),
                    headline=str(card.get("headline", "")),
                    what_it_says=str(card.get("what_it_says", "")),
                    what_it_means=str(card.get("what_it_means", "")),
                    ask_them=ask_str,
                    keywords=_tokenize(f"{clause_text} {topic}"),
                )
            )
    except OSError, ValueError:
        return ()

    return tuple(exemplars)


def retrieve_annotated_exemplar(
    clause_text: str,
    contract_type: str | None = None,
) -> AnnotatedExemplar | None:
    """Retrieve the closest legal-expert annotated exemplar from memory in <0.5 ms."""
    exemplars = load_annotated_exemplars()
    if not exemplars:
        return None

    query_tokens = _tokenize(clause_text)
    if not query_tokens:
        return None

    best_score = 0
    best_exemplar: AnnotatedExemplar | None = None
    for ex in exemplars:
        overlap = len(query_tokens & ex.keywords)
        if contract_type and ex.contract_type == contract_type and overlap > 0:
            overlap += 2
        if overlap > best_score:
            best_score = overlap
            best_exemplar = ex

    return best_exemplar if best_score >= 2 else None


def retrieve_simple_evidence(clause_text: str, max_items: int = 1) -> list[Evidence]:
    """Retrieve best-matching synthetic template evidence based on keyword heuristics.

    Args:
        clause_text: Extracted text of the clause to match.
        max_items: Maximum number of template excerpts to return.

    Returns:
        List of Evidence objects with assigned stable evidence IDs.
    """
    text_lower = clause_text.lower()
    scored: list[tuple[int, SyntheticTemplateClause]] = []

    for template in SYNTHETIC_CORPUS:
        score = sum(1 for kw in template.keywords if kw in text_lower)
        if score > 0:
            scored.append((score, template))

    # Sort descending by score
    scored.sort(key=lambda item: item[0], reverse=True)

    results: list[Evidence] = []
    for idx, (_, template) in enumerate(scored[:max_items], start=1):
        results.append(template.to_evidence(f"ev-{idx}"))

    # If no keywords matched, provide general royalty or rights standard as default candidate
    if not results and SYNTHETIC_CORPUS:
        results.append(SYNTHETIC_CORPUS[0].to_evidence("ev-1"))

    return results
