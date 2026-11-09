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
    contract_type: str = "general_music"
    drafted_for: str = "neutral"

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
        contract_type="recording",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-recoupment",
        source_title="KECOBO Standard Guidance on Recording Deals",
        jurisdiction="KE",
        topic="advances_recoupment",
        excerpt=(
            "Direct recording and production costs approved in advance in writing shall be "
            "recoupable solely from the Artist's accrued royalties. In no event shall the Artist "
            "be personally liable to repay unrecouped balances, nor shall income from live gigs "
            "or outside work be garnished for recoupment."
        ),
        keywords=("recoup", "recoupable", "recoupment", "advance", "costs", "studio", "expenses"),
        contract_type="recording",
        drafted_for="artist",
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
        contract_type="recording",
        drafted_for="neutral",
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap130-grant-of-rights",
        source_title="Kenya Copyright Act (Cap. 130) Standard Assignment Provisions",
        jurisdiction="KE",
        topic="grant_of_rights",
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
        contract_type="recording",
        drafted_for="artist",
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
        contract_type="recording",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-wipo-accounting-audit",
        source_title="WIPO Guide on Music Contracts (Model Agreement)",
        jurisdiction="KE / International",
        topic="accounting_audit",
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
        contract_type="recording",
        drafted_for="neutral",
    ),
    SyntheticTemplateClause(
        template_id="tpl-live-gig-compensation",
        source_title="Kenyan Live Performance Standard Terms",
        jurisdiction="KE",
        topic="payment",
        excerpt=(
            "The Promoter shall pay the Artist a guaranteed fee with a minimum 50% "
            "non-refundable deposit payable upon execution, and the remaining balance "
            "immediately prior to or upon conclusion of the performance. Local hospitality "
            "and technical rider items shall be provided."
        ),
        keywords=("live", "gig", "performance", "promoter", "fee", "deposit", "venue", "rider"),
        contract_type="live_performance",
        drafted_for="artist",
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
        contract_type="general_music",
        drafted_for="neutral",
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-sync-endorsement",
        source_title=(
            "KECOBO Standard Synchronization & Brand Endorsement Guidelines / "
            "Kenya Data Protection Act (2019)"
        ),
        jurisdiction="KE",
        topic="grant_of_rights",
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
        contract_type="synchronization",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap130-moral-rights-reversion",
        source_title="Kenya Copyright Act (Cap. 130, Sections 32 & 33) — Moral Rights & Assignment",
        jurisdiction="KE",
        topic="moral_rights",
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
        contract_type="publishing",
        drafted_for="artist",
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
        contract_type="publishing",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap229a-performers-rights",
        source_title="Performers Protection Act (Cap. 229A, Laws of Kenya)",
        jurisdiction="KE",
        topic="grant_of_rights",
        excerpt=(
            "Under the Performers Protection Act (Cap. 229A), no person shall broadcast, "
            "record, or make a commercial fixation of a Performer's live performance without "
            "the Performer's express written consent and separate equitable remuneration."
        ),
        keywords=("fixation", "broadcast", "livestream", "filming", "performer", "229a"),
        contract_type="live_performance",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-wipo-management-sunset",
        source_title="WIPO & Music Managers Forum (MMF) Standard Management Agreement",
        jurisdiction="KE / International",
        topic="payment",
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
        contract_type="management",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-producer-splits",
        source_title="KECOBO Standard Recording-Producer Agreement & Split-Sheet",
        jurisdiction="KE",
        topic="royalties",
        excerpt=(
            "Where a Studio Producer contributes original musical composition (the Beat), the "
            "Producer and Artist shall execute a written Split Sheet recognizing the Producer's "
            "50% underlying composition share alongside a 3% to 4% PPD producer royalty on the "
            "master sound recording."
        ),
        keywords=("producer", "beat", "split", "stems", "trackouts", "instrumental", "ppd"),
        contract_type="producer",
        drafted_for="neutral",
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
        contract_type="distribution",
        drafted_for="artist",
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
        contract_type="general_music",
        drafted_for="neutral",
    ),
    SyntheticTemplateClause(
        template_id="tpl-ncia-mediation-disputes",
        source_title="KECOBO & Nairobi Centre for International Arbitration (NCIA) Dispute Clause",
        jurisdiction="KE",
        topic="dispute_resolution",
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
        contract_type="general_music",
        drafted_for="neutral",
    ),
    SyntheticTemplateClause(
        template_id="tpl-recording-digital-deductions",
        source_title="KECOBO Standard Recording Agreement Guidelines",
        jurisdiction="KE",
        topic="royalties",
        excerpt=(
            "No packaging deductions, container charges, free goods allowances, or digital tech "
            "fees shall be deducted from digital audio streams, permanent downloads, or telecom "
            "ringback tunes. Digital royalties shall be accounted on gross wholesale receipts."
        ),
        keywords=(
            "packaging",
            "container",
            "free goods",
            "deduction",
            "digital",
            "streams",
            "tech fee",
        ),
        contract_type="recording",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-recording-master-reversion",
        source_title="KECOBO & WIPO Master Rights Reversion Standard",
        jurisdiction="KE / International",
        topic="grant_of_rights",
        excerpt=(
            "All rights, title, and copyright in the Master Sound Recordings shall revert 100% "
            "to the Artist upon full recoupment of approved recording costs, or within five (5) "
            "to seven (7) years from initial commercial release."
        ),
        keywords=("reversion", "revert", "masters", "term", "recoupment", "retention"),
        contract_type="recording",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-management-key-man",
        source_title="Music Managers Forum (MMF) & WIPO Key-Man Guidance",
        jurisdiction="KE / International",
        topic="termination",
        excerpt=(
            "The personal management services of the named Lead Manager are essential to this "
            "Agreement. If the Lead Manager leaves the management firm or ceases active "
            "day-to-day representation, the Artist may terminate this Agreement immediately "
            "upon written notice without penalty."
        ),
        keywords=("key man", "key-man", "lead manager", "personal services", "manager", "firm"),
        contract_type="management",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-management-gross-exclusions",
        source_title="MMF Standard Artist Management Model Agreement",
        jurisdiction="KE / International",
        topic="payment",
        excerpt=(
            "Manager commissions shall apply strictly to Net Receipts actually received by the "
            "Artist. Approved recording budgets, video production funds, tour support deficits, "
            "sound reinforcement fees, and backing musicians' wages shall be excluded from "
            "commissionable gross income."
        ),
        keywords=(
            "commission",
            "net receipts",
            "exclusions",
            "tour support",
            "video budget",
            "recording fund",
        ),
        contract_type="management",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-management-term-targets",
        source_title="WIPO Model Artist Management Agreement",
        jurisdiction="KE / International",
        topic="term",
        excerpt=(
            "The initial term shall be two (2) years. Renewal for any subsequent option period is "
            "conditional on the Manager securing verifiable minimum gross entertainment income "
            "milestones for the Artist during the preceding term."
        ),
        keywords=("milestones", "targets", "renewal", "income target", "term", "option"),
        contract_type="management",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-publishing-at-source",
        source_title="CISAC & International Music Publishers Standard Benchmarks",
        jurisdiction="KE / International",
        topic="royalties",
        excerpt=(
            "Publishing royalties shall be accounted and paid on an 'At Source' basis in the "
            "country of exploitation, without foreign sub-publisher fee deduction exceeding "
            "fifteen percent (15%) prior to calculation of the Writer and Publisher shares."
        ),
        keywords=("at source", "sub-publisher", "publishing", "royalties", "foreign", "deduction"),
        contract_type="publishing",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-publishing-unexploited-reversion",
        source_title="KECOBO Music Publishing Advisory Guidelines",
        jurisdiction="KE",
        topic="grant_of_rights",
        excerpt=(
            "Any musical composition not commercially recorded, synchronized, or publicly "
            "exploited within twenty-four (24) months from delivery shall revert 100% to the "
            "Songwriter, and the Publisher shall execute all reassignment instruments."
        ),
        keywords=(
            "unexploited",
            "reversion",
            "reassignment",
            "24 months",
            "unreleased",
            "publishing",
        ),
        contract_type="publishing",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-publishing-sync-approvals",
        source_title="WIPO & KECOBO Songwriter Creative Rights Guidance",
        jurisdiction="KE / International",
        topic="warranties_indemnities",
        excerpt=(
            "The Publisher shall obtain prior written consent from the Songwriter before "
            "licensing any composition for synchronisation with political campaigns, alcohol, "
            "tobacco, gambling, betting, or generative AI model training."
        ),
        keywords=("sync", "approval", "consent", "political", "gambling", "tobacco", "ai model"),
        contract_type="publishing",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-sync-brand-production-costs",
        source_title="KECOBO Brand Endorsement & Influencer Agreement Model",
        jurisdiction="KE",
        topic="payment",
        excerpt=(
            "The Brand shall bear 100% of all photography, audio/video production, wardrobe, "
            "media boosting, and travel expenses. No production or marketing costs may be "
            "recouped from or offset against the Artist's guaranteed endorsement fee."
        ),
        keywords=(
            "production costs",
            "brand",
            "endorsement",
            "fee",
            "expenses",
            "recoupable",
            "media",
        ),
        contract_type="synchronization",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-sync-brand-category-exclusivity",
        source_title="KECOBO Brand Partnership Guidelines",
        jurisdiction="KE",
        topic="exclusivity",
        excerpt=(
            "Exclusivity granted to the Brand shall be limited strictly to direct commercial "
            "competitors in the designated product sub-category during the active Campaign Term, "
            "and shall not include post-term cooling-off restrictions or prevent live performances."
        ),
        keywords=("exclusivity", "category", "cooling-off", "brand", "competitors", "campaign"),
        contract_type="synchronization",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-producer-sample-warranty",
        source_title="KECOBO Producer & Beat Lease Standard Warranty",
        jurisdiction="KE",
        topic="warranties_indemnities",
        excerpt=(
            "The Producer warrants that the beat is 100% original, contains no uncleared "
            "third-party samples or interpolations, and indemnifies the Artist against any "
            "third-party copyright claims or liabilities."
        ),
        keywords=("sample", "warranty", "original", "uncleared", "indemnity", "producer", "beat"),
        contract_type="producer",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-producer-exclusive-beat",
        source_title="KECOBO Studio Production Model Contract",
        jurisdiction="KE",
        topic="exclusivity",
        excerpt=(
            "Upon payment of the agreed production fee, the instrumental beat is licensed or "
            "assigned exclusively to the Artist. The Producer shall not resell, re-license, lease, "
            "or distribute the beat or underlying trackout stems to any other party."
        ),
        keywords=("exclusive", "beat", "stems", "trackouts", "lease", "resell", "producer"),
        contract_type="producer",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-distribution-master-retention",
        source_title="KECOBO Digital Aggregator Guidance",
        jurisdiction="KE",
        topic="grant_of_rights",
        excerpt=(
            "The Digital Aggregator agreement is strictly a distribution service license. "
            "The Artist retains 100% copyright in all Master Sound Recordings, metadata, "
            "catalog assets, and ISRC registrations."
        ),
        keywords=("ownership", "retention", "masters", "isrc", "distribution", "aggregator"),
        contract_type="distribution",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-live-radius-clause",
        source_title="Musicians' Union & KECOBO Live Performance Radii Standard",
        jurisdiction="KE",
        topic="exclusivity",
        excerpt=(
            "Performance radius restrictions shall apply strictly to public ticketed concerts "
            "within a maximum of fifty (50) kilometres and sixty (60) days of the event, "
            "expressly excluding private corporate, wedding, and non-ticketed club appearances."
        ),
        keywords=("radius", "blackout", "distance", "kilometres", "festival", "booking", "live"),
        contract_type="live_performance",
        drafted_for="artist",
    ),
    SyntheticTemplateClause(
        template_id="tpl-general-credit-attribution",
        source_title="Kenya Copyright Act (Cap. 130, Section 32) & WIPO Moral Attribution Standard",
        jurisdiction="KE / International",
        topic="credit",
        excerpt=(
            "The Artist, Songwriter, and Producer shall receive appropriate, prominent credit "
            "attribution on all physical and digital releases, streaming metadata, liner notes, "
            "and promotional materials in accordance with Section 32 of Cap. 130."
        ),
        keywords=("credit", "attribution", "paternity", "metadata", "liner notes", "billing"),
        contract_type="general_music",
        drafted_for="artist",
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
