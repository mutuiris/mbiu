"""Check, tag and embed split clauses, then publish them as a new corpus version."""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from django.db import transaction

from mbiu.corpus.models import CorpusVersion, PipelineCheckResult, ReferenceChunk, ReferenceSource
from mbiu.pipeline.checks import (
    CheckResult,
    EnglishDetector,
    PersonalDataFinder,
    agreed_tags,
    check_english,
    check_metadata,
    check_near_duplicates,
    check_personal_data,
    check_standard_template,
    check_tag_agreement,
)
from mbiu.pipeline.embed import Embedder, embed_clauses, pattern_counts
from mbiu.pipeline.errors import PipelineError
from mbiu.pipeline.models import TemplateClause
from mbiu.pipeline.tag import Tagger, chunk_key, tag_clauses

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublishTools:
    """The models and detectors a publish run uses."""

    taggers: Sequence[Tagger]
    find_personal_data: PersonalDataFinder
    is_english: EnglishDetector
    embedder: Embedder


def publish_corpus(
    clauses: Sequence[TemplateClause],
    tools: PublishTools,
    *,
    version_tag: str,
    concurrency: int,
    timeout_s: float,
) -> CorpusVersion:
    """Run every check, write a new version with its chunks and results, then activate it.

    Raises:
        PipelineError: If the tag exists, no clause passes every check, or embedding fails.
        LLMError: If a tagging call fails, so no clause is dropped for a missing vote.
    """
    if len(tools.taggers) < 2:
        raise PipelineError("tag agreement needs two independent models")
    if CorpusVersion.objects.filter(version_tag=version_tag).exists():
        raise PipelineError(f"corpus version {version_tag} already exists; use a new tag")

    checks: list[CheckResult] = []
    kept, result = check_metadata(clauses)
    checks.append(result)
    kept, result = check_personal_data(kept, tools.find_personal_data)
    checks.append(result)
    kept, result = check_english(kept, tools.is_english)
    checks.append(result)
    kept, result = check_near_duplicates(kept)
    checks.append(result)
    votes = asyncio.run(
        tag_clauses(kept, tools.taggers, concurrency=concurrency, timeout_s=timeout_s)
    )
    kept, result = check_standard_template(kept, votes)
    checks.append(result)
    kept, result = check_tag_agreement(kept, votes)
    checks.append(result)

    for check in checks:
        logger.info("Check %s rejected %d of %d", check.name, len(check.rejected), check.checked)
    if not kept:
        raise PipelineError("no clause passed every check; nothing to publish")

    vectors = embed_clauses(kept, tools.embedder)
    counts = pattern_counts(vectors)

    with transaction.atomic():
        version = CorpusVersion.objects.create(
            version_tag=version_tag,
            embedding_model_id=tools.embedder.model_id,
            embedding_revision=tools.embedder.revision,
        )
        sources: dict[str, ReferenceSource] = {}
        chunks: list[ReferenceChunk] = []
        for clause, vector, count in zip(kept, vectors, counts, strict=True):
            if clause.document_sha256 not in sources:
                sources[clause.document_sha256] = _source(clause)
            tags = agreed_tags(votes[chunk_key(clause)])
            chunks.append(
                ReferenceChunk(
                    corpus_version=version,
                    source=sources[clause.document_sha256],
                    chunk_key=chunk_key(clause),
                    title=(clause.title or "")[:255],
                    text=clause.text,
                    topic=tags.topic,
                    contract_type=tags.contract_type,
                    jurisdiction=tags.jurisdiction,
                    drafted_for=tags.drafted_for,
                    pattern_count=count,
                    embedding=vector,
                )
            )
        ReferenceChunk.objects.bulk_create(chunks)
        PipelineCheckResult.objects.bulk_create(
            PipelineCheckResult(
                corpus_version=version,
                check_name=check.name,
                passed=check.passed,
                details=check.details,
            )
            for check in checks
        )

    CorpusVersion.activate(version_tag)
    logger.info("Published corpus %s with %d chunks", version_tag, len(chunks))
    return version


def _source(clause: TemplateClause) -> ReferenceSource:
    """Reuse an identical source row, never edit one: older versions still point at it."""
    fields = {
        "title": _title(clause.source_url),
        "url": clause.source_url,
        "document_sha256": clause.document_sha256,
        "licence": clause.licence,
        "reviewing_body": clause.reviewing_body,
        "template_version": clause.template_version,
        "contract_type": clause.contract_type,
        "jurisdiction": clause.jurisdiction,
    }
    existing = ReferenceSource.objects.filter(**fields).first()
    return existing or ReferenceSource.objects.create(**fields)


def _title(url: str) -> str:
    parts = urlsplit(url)
    return (PurePosixPath(unquote(parts.path)).stem.strip() or parts.netloc)[:255]
