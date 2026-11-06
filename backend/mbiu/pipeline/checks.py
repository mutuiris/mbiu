"""The automatic checks every template clause must pass before it is published.

No person reviews the corpus, so these checks are what keep articles, sales pages and
signed deals out of the standard. A document that fails a document check is dropped
whole; a clause that fails a clause check is dropped alone.
"""

import hashlib
import importlib
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from mbiu.pipeline.models import TemplateClause
from mbiu.pipeline.tag import ClauseTags, chunk_key

PersonalDataFinder = Callable[[str], set[str]]
EnglishDetector = Callable[[str], bool]
_Hashes = npt.NDArray[np.uint64]

NEAR_DUPLICATE_SIMILARITY = 0.85
_MINHASH_PERMUTATIONS = 128
_MINHASH_PRIME = (1 << 31) - 1
_PLACEHOLDER = re.compile(r"\[[^\]]*\]|<[^>]*>|_{3,}|\.{4,}")


@dataclass
class CheckResult:
    """What one check rejected, stored with the version it checked."""

    name: str
    checked: int = 0
    rejected: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True when the check rejected nothing."""
        return not self.rejected

    @property
    def details(self) -> dict[str, Any]:
        """JSON stored in ``pipeline_check_results``. Never holds the flagged text."""
        return {"checked": self.checked, "rejected": self.rejected}


def check_metadata(clauses: Sequence[TemplateClause]) -> tuple[list[TemplateClause], CheckResult]:
    """Drop documents without a licence, jurisdiction or reviewing body."""

    def missing(clause: TemplateClause) -> list[str]:
        fields = {
            "licence": clause.licence,
            "jurisdiction": clause.jurisdiction,
            "reviewing_body": clause.reviewing_body,
        }
        return sorted(name for name, value in fields.items() if not value.strip())

    return _check_documents("metadata", clauses, lambda doc: _reason(missing(doc[0]), "missing"))


def check_personal_data(
    clauses: Sequence[TemplateClause], find: PersonalDataFinder
) -> tuple[list[TemplateClause], CheckResult]:
    """Drop any document where personal data is found: it is a filled-in deal, not a template.

    Only the entity types are recorded, never the text that matched.
    """

    def entities(doc: list[TemplateClause]) -> list[str]:
        found: set[str] = set()
        for clause in doc:
            found |= find(_PLACEHOLDER.sub(" ", clause.text))
        return sorted(found)

    return _check_documents("personal_data", clauses, lambda doc: _reason(entities(doc), "found"))


def check_english(
    clauses: Sequence[TemplateClause], is_english: EnglishDetector
) -> tuple[list[TemplateClause], CheckResult]:
    """Drop documents whose text is not English."""
    return _check_documents(
        "english",
        clauses,
        lambda doc: None if is_english("\n".join(c.text for c in doc)) else "not English",
    )


def check_near_duplicates(
    clauses: Sequence[TemplateClause], threshold: float = NEAR_DUPLICATE_SIMILARITY
) -> tuple[list[TemplateClause], CheckResult]:
    """Keep the first of any clauses whose MinHash similarity reaches ``threshold``."""
    result = CheckResult("near_duplicates", checked=len(clauses))
    rng = np.random.default_rng(0)
    a = rng.integers(1, _MINHASH_PRIME, _MINHASH_PERMUTATIONS, dtype=np.uint64)
    b = rng.integers(0, _MINHASH_PRIME, _MINHASH_PERMUTATIONS, dtype=np.uint64)
    kept: list[TemplateClause] = []
    signatures: list[_Hashes] = []
    for clause in clauses:
        signature = _minhash(clause.text, a, b)
        if signatures:
            similarity = (np.vstack(signatures) == signature).mean(axis=1)
            best = int(similarity.argmax())
            if similarity[best] >= threshold:
                result.rejected.append(
                    {
                        "chunk_key": chunk_key(clause),
                        "reason": f"near-duplicate of {chunk_key(kept[best])}",
                        "similarity": round(float(similarity[best]), 3),
                    }
                )
                continue
        kept.append(clause)
        signatures.append(signature)
    return kept, result


def check_standard_template(
    clauses: Sequence[TemplateClause], votes: Mapping[str, Sequence[ClauseTags]]
) -> tuple[list[TemplateClause], CheckResult]:
    """Keep a clause only if every model confirms it is standard template wording."""

    def reason(clause: TemplateClause) -> str | None:
        answers = votes.get(chunk_key(clause))
        if not answers or not all(tags.is_standard_template for tags in answers):
            return "a model did not confirm it is standard template wording"
        return None

    return _check_clauses("standard_template", clauses, reason)


def check_tag_agreement(
    clauses: Sequence[TemplateClause], votes: Mapping[str, Sequence[ClauseTags]]
) -> tuple[list[TemplateClause], CheckResult]:
    """Keep a clause only if the models gave it the same tags."""

    def reason(clause: TemplateClause) -> str | None:
        answers = votes.get(chunk_key(clause), [])
        if len(answers) < 2:
            return "fewer than two models tagged it"
        disagree = [
            name
            for name in ("contract_type", "topic", "jurisdiction", "drafted_for")
            if len({_tag_value(tags, name) for tags in answers}) > 1
        ]
        return _reason(disagree, "models disagree on")

    return _check_clauses("tag_agreement", clauses, reason)


def agreed_tags(answers: Sequence[ClauseTags]) -> ClauseTags:
    """The shared tags of a clause that passed the agreement check."""
    tags = answers[0]
    return tags.model_copy(update={"jurisdiction": _tag_value(tags, "jurisdiction")})


class PresidioFinder:
    """Personal-data detection with Presidio and its default English spaCy model."""

    ENTITIES = (
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "IBAN_CODE",
        "IP_ADDRESS",
        "CRYPTO",
    )

    def __init__(self, score_threshold: float = 0.5) -> None:
        """Load the analyzer once; it takes several seconds."""
        presidio = importlib.import_module("presidio_analyzer")
        self._analyzer = presidio.AnalyzerEngine(supported_languages=["en"])
        self._score_threshold = score_threshold

    def __call__(self, text: str) -> set[str]:
        """Return the personal-data entity types found in ``text``."""
        results = self._analyzer.analyze(
            text=text,
            language="en",
            entities=list(self.ENTITIES),
            score_threshold=self._score_threshold,
        )
        return {str(result.entity_type) for result in results}


class LinguaDetector:
    """Language detection with Lingua."""

    def __init__(self) -> None:
        """Build the detector over every language Lingua knows."""
        lingua = importlib.import_module("lingua")
        self._english = lingua.Language.ENGLISH
        builder = lingua.LanguageDetectorBuilder.from_all_languages()
        self._detector = builder.with_low_accuracy_mode().build()

    def __call__(self, text: str) -> bool:
        """True when Lingua's best guess for ``text`` is English."""
        return bool(self._detector.detect_language_of(text) == self._english)


def _check_documents(
    name: str,
    clauses: Sequence[TemplateClause],
    reason: Callable[[list[TemplateClause]], str | None],
) -> tuple[list[TemplateClause], CheckResult]:
    documents: dict[str, list[TemplateClause]] = defaultdict(list)
    for clause in clauses:
        documents[clause.document_sha256].append(clause)
    result = CheckResult(name, checked=len(documents))
    dropped: set[str] = set()
    for sha256, doc in documents.items():
        why = reason(doc)
        if why is not None:
            dropped.add(sha256)
            result.rejected.append(
                {"document_sha256": sha256, "source_url": doc[0].source_url, "reason": why}
            )
    return [c for c in clauses if c.document_sha256 not in dropped], result


def _check_clauses(
    name: str,
    clauses: Sequence[TemplateClause],
    reason: Callable[[TemplateClause], str | None],
) -> tuple[list[TemplateClause], CheckResult]:
    result = CheckResult(name, checked=len(clauses))
    kept: list[TemplateClause] = []
    for clause in clauses:
        why = reason(clause)
        if why is None:
            kept.append(clause)
        else:
            result.rejected.append({"chunk_key": chunk_key(clause), "reason": why})
    return kept, result


def _reason(items: list[str], prefix: str) -> str | None:
    return f"{prefix}: {', '.join(items)}" if items else None


def _tag_value(tags: ClauseTags, name: str) -> str:
    value = str(getattr(tags, name)).strip()
    if name == "jurisdiction":
        return value.upper() if len(value) == 2 else value.casefold()
    return value


def _minhash(text: str, a: _Hashes, b: _Hashes) -> _Hashes:
    words = re.findall(r"\w+", text.casefold())
    shingles = {" ".join(words[i : i + 3]) for i in range(max(1, len(words) - 2))}
    hashes = np.array(
        [
            int.from_bytes(hashlib.blake2b(s.encode(), digest_size=4).digest()) % _MINHASH_PRIME
            for s in shingles
        ],
        dtype=np.uint64,
    )
    signature: _Hashes = ((np.outer(hashes, a) + b) % _MINHASH_PRIME).min(axis=0)
    return signature
