"""Automated quality checks module for corpus pipeline.

All six checks must pass before publishing a corpus release:
1. Metadata validation: license, jurisdiction, and reviewing body present and verified.
2. Template validation: heuristic/model check confirms operative standard template nature.
3. PII / Personal Data scan: scanner ensures zero personal data appears in public templates.
4. Language check: confirms text is English.
5. Deduplication check: MinHash / n-gram Jaccard near-duplicate removal.
6. Tag consensus check: dual-tagger agreement.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from mbiu.corpus.pipeline.tag import TaggingResult

logger = logging.getLogger(__name__)

# Permitted open / reusable licenses for reference standards
VALID_LICENSES: frozenset[str] = frozenset(
    {
        "cc by 4.0",
        "cc by-sa 4.0",
        "cc by-nc 4.0",
        "cc by 3.0",
        "cc0",
        "cc0 1.0",
        "public domain",
        "open government licence",
        "open government license",
        "ogl-3.0",
        "statutory guidance",
        "kenya copyright act (cap. 130)",
        "wipo reference standard",
        "permissive educational",
    }
)

# Common English stop words and contract terms for language verification
COMMON_ENGLISH_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "be",
        "to",
        "of",
        "and",
        "a",
        "in",
        "that",
        "have",
        "has",
        "had",
        "i",
        "it",
        "for",
        "not",
        "on",
        "with",
        "he",
        "as",
        "you",
        "do",
        "does",
        "did",
        "at",
        "this",
        "but",
        "his",
        "by",
        "from",
        "they",
        "we",
        "say",
        "her",
        "she",
        "or",
        "an",
        "will",
        "my",
        "one",
        "all",
        "would",
        "there",
        "their",
        "what",
        "so",
        "up",
        "out",
        "if",
        "about",
        "who",
        "get",
        "which",
        "go",
        "me",
        "when",
        "make",
        "can",
        "like",
        "time",
        "no",
        "just",
        "him",
        "know",
        "take",
        "shall",
        "should",
        "could",
        "may",
        "might",
        "must",
        "agreement",
        "party",
        "parties",
        "contract",
        "terms",
        "clause",
        "rights",
        "royalties",
        "royalty",
        "payment",
        "payments",
        "license",
        "licensee",
        "licensor",
        "hereunder",
        "artist",
        "company",
        "record",
        "recording",
        "music",
        "musical",
        "master",
        "sound",
        "herein",
        "thereof",
        "provided",
        "subject",
        "exclusive",
        "audit",
        "books",
        "breach",
        "written",
        "notice",
        "effective",
        "date",
        "term",
        "period",
        "law",
        "laws",
        "court",
        "jurisdiction",
        "dispute",
        "arbitration",
        "warrant",
        "represent",
        "indemnify",
        "costs",
        "expenses",
        "receipts",
        "gross",
        "net",
        "manager",
        "management",
        "render",
        "true",
        "accurate",
        "monthly",
        "statements",
        "statement",
        "annual",
        "semi",
        "quarterly",
        "commission",
        "commissions",
        "author",
        "authors",
        "work",
        "works",
        "performance",
        "performer",
        "moral",
        "paternity",
        "integrity",
        "recoup",
        "recoupable",
        "recoupment",
        "advance",
        "advances",
        "earnings",
        "derived",
        "activities",
        "negotiated",
        "during",
        "expense",
        "prior",
        "inspect",
        "records",
        "relating",
        "distortion",
        "mutilation",
        "modification",
        "claim",
        "authorship",
        "object",
        "wholesale",
        "stream",
        "streams",
        "under",
        "each",
        "other",
        "any",
        "been",
        "being",
        "between",
        "both",
        "such",
        "than",
        "then",
        "into",
        "through",
        "before",
        "after",
        "above",
        "below",
        "same",
        "some",
        "only",
        "own",
        "more",
        "most",
        "also",
        "where",
        "how",
        "over",
    }
)

# Common operative contract language keywords
OPERATIVE_CONTRACT_KEYWORDS: frozenset[str] = frozenset(
    {
        "shall",
        "agrees",
        "undertakes",
        "warrants",
        "represents",
        "hereby",
        "grant",
        "rights",
        "terms",
        "conditions",
        "royalties",
        "payment",
        "license",
        "recoup",
        "advance",
        "termination",
        "indemnify",
        "governing law",
        "jurisdiction",
        "parties",
    }
)


@dataclass(frozen=True)
class TemplateSourceData:
    """Metadata describing a reference document source."""

    title: str
    license: str
    reviewing_body: str
    contract_type: str
    jurisdiction: str = "KE"
    url: str = ""


@dataclass(frozen=True)
class TemplateClauseData:
    """A standard template clause candidate for the corpus."""

    chunk_key: str
    text: str
    source: TemplateSourceData
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckOutcome:
    """Result of an automated pipeline verification check."""

    check_name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


# --- 1. Metadata Validation ---


def validate_metadata(sources: list[TemplateSourceData]) -> CheckOutcome:
    """Validate that every template source has verified license, jurisdiction, and reviewing body.

    Rejects missing, blank, or proprietary licenses (e.g. 'All Rights Reserved').
    """
    if not sources:
        return CheckOutcome(
            check_name="metadata_validation",
            passed=False,
            details={"error": "No template sources provided"},
        )

    invalid_sources: list[dict[str, str]] = []

    for src in sources:
        errors: list[str] = []
        if not src.title or not src.title.strip():
            errors.append("Missing title")

        clean_license = src.license.strip().lower()
        if not clean_license:
            errors.append("Missing license")
        elif clean_license not in VALID_LICENSES:
            errors.append(f"Unverified or proprietary license: '{src.license}'")

        if not src.reviewing_body or not src.reviewing_body.strip():
            errors.append("Missing reviewing_body")

        if not src.jurisdiction or not src.jurisdiction.strip():
            errors.append("Missing jurisdiction")

        if errors:
            invalid_sources.append(
                {
                    "title": src.title,
                    "errors": "; ".join(errors),
                }
            )

    passed = len(invalid_sources) == 0
    return CheckOutcome(
        check_name="metadata_validation",
        passed=passed,
        details={
            "total_sources": len(sources),
            "invalid_count": len(invalid_sources),
            "invalid_sources": invalid_sources,
        },
    )


# --- 2. Template Validation ---


def validate_template_nature(clauses: list[TemplateClauseData]) -> CheckOutcome:
    """Verify clauses represent operative standard template wording.

    Rejects:
    - Signed contracts with real party execution blocks or witness signatures.
    - Marketing copy, sales pitches, or website advertisements.
    - Informal blog posts or non-operative discussion articles.
    """
    if not clauses:
        return CheckOutcome(
            check_name="template_validation",
            passed=False,
            details={"error": "No clauses provided for validation"},
        )

    invalid_clauses: list[dict[str, Any]] = []

    # Indicators of marketing copy
    marketing_patterns = [
        re.compile(
            r"\b(?:buy now|subscribe today|click here|limited time offer|discount code)\b", re.I
        ),
        re.compile(r"\b(?:contact us for a quote|best music distribution platform)\b", re.I),
    ]

    # Indicators of signed/executed contracts
    signed_patterns = [
        re.compile(r"\bin witness whereof the parties have executed\b.*?\b(?:19|20)\d{2}\b", re.I),
        re.compile(r"\bsigned by the said\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+on\b", re.I),
    ]

    # Indicators of blog or editorial articles
    blog_patterns = [
        re.compile(r"\b(?:in this article we will explore|welcome to our blog)\b", re.I),
    ]

    for clause in clauses:
        text = clause.text
        lower = text.lower()
        reasons: list[str] = []

        # Check marketing
        if any(pat.search(text) for pat in marketing_patterns):
            reasons.append("Marketing or promotional copy detected")

        # Check executed contract
        if any(pat.search(text) for pat in signed_patterns):
            reasons.append("Executed/signed contract signature block detected")

        # Check blog prose
        if any(pat.search(text) for pat in blog_patterns):
            reasons.append("Editorial or blog article text detected")

        # Check for operative legal language
        words = set(re.findall(r"\b[a-z]{3,}\b", lower))
        matching_keywords = words.intersection(OPERATIVE_CONTRACT_KEYWORDS)
        if len(matching_keywords) < 1 and len(text.split()) > 10:
            reasons.append("Lacks operative legal/contractual language")

        if reasons:
            invalid_clauses.append(
                {
                    "chunk_key": clause.chunk_key,
                    "reasons": reasons,
                    "snippet": text[:120],
                }
            )

    passed = len(invalid_clauses) == 0
    return CheckOutcome(
        check_name="template_validation",
        passed=passed,
        details={
            "total_clauses": len(clauses),
            "invalid_count": len(invalid_clauses),
            "invalid_clauses": invalid_clauses,
        },
    )


# --- 3. PII / Personal Data Scanner ---


# Standard placeholder names allowed in templates
ALLOWED_PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {
        "john doe",
        "jane doe",
        "party a",
        "party b",
        "the artist",
        "the company",
        "the manager",
        "the producer",
        "the label",
        "abc records",
        "xyz music",
        "wipo",
        "kecobo",
        "kenya copyright board",
    }
)

EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
KENYA_PHONE_REGEX = re.compile(r"(?:\+?254|0)[\s.-]?[17](?:[\s.-]?\d){8}\b")
STREET_ADDRESS_REGEX = re.compile(
    r"\b\d{1,5}\s+(?:[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:Street|Road|Avenue|Lane|Way|Drive|Boulevard|Blvd|Highway|Close|Plaza)\b",
    re.I,
)
PO_BOX_REGEX = re.compile(r"\b(?:P\.?\s*O\.?\s*Box)\s+\d+\b", re.I)
NATIONAL_ID_REGEX = re.compile(
    r"\b(?:ID\s*(?:No\.?|Number)?|National\s*ID|SSN|Passport\s*(?:No\.?)?)\s*[:#-]?\s*([0-9A-Z]{6,12})\b",
    re.I,
)


def scan_for_pii(clauses: list[TemplateClauseData]) -> CheckOutcome:
    """Scan candidate clauses to guarantee zero personal data in public templates.

    Allows valid template placeholders (e.g. '[Artist Name]', '<Email Address>',
    'Party A', 'Jane Doe') but rejects real personal emails, phone numbers,
    private physical addresses, and national identification numbers.
    """
    violations: list[dict[str, Any]] = []

    for clause in clauses:
        text = clause.text

        # 1. Mask allowable bracket placeholders first: [Artist Name], <insert email>, etc.
        masked_text = re.sub(r"\[[^\]]+\]", " [PLACEHOLDER] ", text)
        masked_text = re.sub(r"<[^>]+>", " <PLACEHOLDER> ", masked_text)

        # 2. Check for real email addresses
        for email_match in EMAIL_REGEX.finditer(masked_text):
            email = email_match.group(0).lower()
            if not any(
                allowed in email
                for allowed in ["example.com", "example.org", "wipo.int", "placeholder"]
            ):
                violations.append(
                    {
                        "chunk_key": clause.chunk_key,
                        "type": "email",
                        "match": email,
                        "snippet": text[
                            max(0, email_match.start() - 20) : min(
                                len(text), email_match.end() + 20
                            )
                        ],
                    }
                )

        # 3. Check for phone numbers
        # Filter for genuine phone numbers (Kenya or international format)
        for phone_match in KENYA_PHONE_REGEX.finditer(masked_text):
            violations.append(
                {
                    "chunk_key": clause.chunk_key,
                    "type": "kenyan_phone_number",
                    "match": phone_match.group(0),
                    "snippet": text[
                        max(0, phone_match.start() - 20) : min(len(text), phone_match.end() + 20)
                    ],
                }
            )

        # 4. Check for physical street addresses and P.O. Box addresses
        for addr_match in STREET_ADDRESS_REGEX.finditer(masked_text):
            violations.append(
                {
                    "chunk_key": clause.chunk_key,
                    "type": "street_address",
                    "match": addr_match.group(0),
                    "snippet": text[
                        max(0, addr_match.start() - 20) : min(len(text), addr_match.end() + 20)
                    ],
                }
            )

        for pobox_match in PO_BOX_REGEX.finditer(masked_text):
            violations.append(
                {
                    "chunk_key": clause.chunk_key,
                    "type": "po_box_address",
                    "match": pobox_match.group(0),
                    "snippet": text[
                        max(0, pobox_match.start() - 20) : min(len(text), pobox_match.end() + 20)
                    ],
                }
            )

        # 5. Check for National ID or Passport numbers
        for id_match in NATIONAL_ID_REGEX.finditer(masked_text):
            violations.append(
                {
                    "chunk_key": clause.chunk_key,
                    "type": "national_id_or_passport",
                    "match": id_match.group(0),
                    "snippet": text[
                        max(0, id_match.start() - 20) : min(len(text), id_match.end() + 20)
                    ],
                }
            )

    passed = len(violations) == 0
    return CheckOutcome(
        check_name="pii_scan",
        passed=passed,
        details={
            "total_clauses": len(clauses),
            "violations_count": len(violations),
            "violations": violations,
        },
    )


# --- 4. Language Check ---


def check_language(
    clauses: list[TemplateClauseData], min_english_ratio: float = 0.50
) -> CheckOutcome:
    """Verify that all template clauses are in English.

    Analyzes vocabulary against standard English word sets.
    Rejects foreign-language or non-English content.
    """
    if not clauses:
        return CheckOutcome(
            check_name="language_check",
            passed=False,
            details={"error": "No clauses provided for language check"},
        )

    non_english_clauses: list[dict[str, Any]] = []

    for clause in clauses:
        text = clause.text
        words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
        if not words:
            non_english_clauses.append(
                {
                    "chunk_key": clause.chunk_key,
                    "reason": "Clause contains no recognizable alphabetic words",
                    "snippet": text[:80],
                }
            )
            continue

        english_matches = sum(1 for w in words if w in COMMON_ENGLISH_WORDS)
        ratio = english_matches / len(words)

        # For short clauses (< 8 words), allow lower threshold if >= 2 english words match
        is_short = len(words) < 8
        is_valid = (ratio >= min_english_ratio) or (is_short and english_matches >= 2)

        if not is_valid:
            non_english_clauses.append(
                {
                    "chunk_key": clause.chunk_key,
                    "english_ratio": round(ratio, 3),
                    "total_words": len(words),
                    "snippet": text[:100],
                }
            )

    passed = len(non_english_clauses) == 0
    return CheckOutcome(
        check_name="language_check",
        passed=passed,
        details={
            "total_clauses": len(clauses),
            "non_english_count": len(non_english_clauses),
            "non_english_clauses": non_english_clauses,
        },
    )


# --- 5. Deduplication Check (MinHash / n-gram Jaccard) ---


def _tokenize_shingles(text: str, n: int = 3) -> set[tuple[str, ...]]:
    """Generate normalized word n-gram shingles."""
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def jaccard_similarity(set_a: set[Any], set_b: set[Any]) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0


def check_deduplication(
    clauses: list[TemplateClauseData],
    similarity_threshold: float = 0.85,
) -> tuple[CheckOutcome, list[TemplateClauseData]]:
    """Deduplicate near-identical template clauses using n-gram Jaccard similarity.

    Retains the first encountered canonical clause and removes redundant duplicates.
    Records deduplication outcome and returns the filtered, deduplicated clause list.
    """
    if not clauses:
        return (
            CheckOutcome(
                check_name="deduplication",
                passed=True,
                details={"original_count": 0, "deduped_count": 0, "duplicates_removed": 0},
            ),
            [],
        )

    deduplicated: list[TemplateClauseData] = []
    shingle_index: list[tuple[set[tuple[str, ...]], TemplateClauseData]] = []
    duplicate_records: list[dict[str, Any]] = []

    for clause in clauses:
        clause_shingles = _tokenize_shingles(clause.text, n=3)
        is_duplicate = False

        for existing_shingles, existing_clause in shingle_index:
            sim = jaccard_similarity(clause_shingles, existing_shingles)
            if sim >= similarity_threshold:
                is_duplicate = True
                duplicate_records.append(
                    {
                        "retained_key": existing_clause.chunk_key,
                        "dropped_key": clause.chunk_key,
                        "similarity": round(sim, 3),
                        "snippet": clause.text[:80],
                    }
                )
                break

        if not is_duplicate:
            shingle_index.append((clause_shingles, clause))
            deduplicated.append(clause)

    outcome = CheckOutcome(
        check_name="deduplication",
        passed=True,
        details={
            "original_count": len(clauses),
            "deduped_count": len(deduplicated),
            "duplicates_removed": len(duplicate_records),
            "duplicate_records": duplicate_records,
        },
    )
    return outcome, deduplicated


# --- 6. Tag Consensus Check ---


def check_tag_consensus(tagging_results: list[TaggingResult]) -> CheckOutcome:
    """Verify that all candidate clauses achieved dual-tagging consensus.

    Only clauses with consensus are accepted into the published corpus.
    """
    if not tagging_results:
        return CheckOutcome(
            check_name="tag_consensus",
            passed=False,
            details={"error": "No tagging results provided for consensus check"},
        )

    disagreements: list[dict[str, Any]] = []

    for res in tagging_results:
        if not res.is_consensus:
            disagreements.append(
                {
                    "clause_key": res.clause_key,
                    "disagreements": res.disagreements,
                    "primary": (
                        {
                            "contract_type": res.primary_tags.contract_type,
                            "topic": res.primary_tags.topic,
                            "drafted_for": res.primary_tags.drafted_for,
                        }
                        if res.primary_tags
                        else None
                    ),
                    "secondary": (
                        {
                            "contract_type": res.secondary_tags.contract_type,
                            "topic": res.secondary_tags.topic,
                            "drafted_for": res.secondary_tags.drafted_for,
                        }
                        if res.secondary_tags
                        else None
                    ),
                }
            )

    passed = len(disagreements) == 0
    return CheckOutcome(
        check_name="tag_consensus",
        passed=passed,
        details={
            "total_clauses": len(tagging_results),
            "consensus_count": len(tagging_results) - len(disagreements),
            "disagreements_count": len(disagreements),
            "disagreements": disagreements,
        },
    )


# --- Orchestrated Verification ---


def run_all_checks(
    sources: list[TemplateSourceData],
    clauses: list[TemplateClauseData],
    tagging_results: list[TaggingResult],
) -> tuple[bool, dict[str, CheckOutcome], list[TemplateClauseData]]:
    """Execute all six automated quality checks over candidate templates.

    Returns:
    - all_passed: bool (True only if every check passed)
    - check_outcomes: dict mapping check_name to CheckOutcome
    - final_clauses: deduplicated list of accepted clauses
    """
    outcomes: dict[str, CheckOutcome] = {}

    # 1. Metadata check
    outcomes["metadata_validation"] = validate_metadata(sources)

    # 2. Template nature check
    outcomes["template_validation"] = validate_template_nature(clauses)

    # 3. PII scan
    outcomes["pii_scan"] = scan_for_pii(clauses)

    # 4. Language check
    outcomes["language_check"] = check_language(clauses)

    # 5. Deduplication check
    dedup_outcome, deduped_clauses = check_deduplication(clauses)
    outcomes["deduplication"] = dedup_outcome

    # 6. Tag consensus check
    outcomes["tag_consensus"] = check_tag_consensus(tagging_results)

    all_passed = all(outcome.passed for outcome in outcomes.values())
    return all_passed, outcomes, deduped_clauses
