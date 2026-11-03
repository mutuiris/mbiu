"""Corpus publishing and orchestration module.

Orchestrates the entire corpus release lifecycle:
1. Dual-tagging consensus.
2. Six automated quality checks (all must pass).
3. n-gram Jaccard deduplication.
4. EmbeddingGemma 2 768-dimensional float32 vector embedding.
5. Commonality and pattern frequency analysis.
6. Atomic database persistence of CorpusVersion, ReferenceChunk, and PipelineCheckResult.
7. Atomic version activation via CorpusVersion.activate_version().
8. In-memory snapshot reload via load_corpus_snapshot().
"""

import datetime
import logging
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from mbiu.corpus.loader import CorpusSnapshot, load_corpus_snapshot
from mbiu.corpus.models import (
    CorpusVersion,
    PipelineCheckResult,
    ReferenceChunk,
    ReferenceSource,
)
from mbiu.corpus.pipeline.checks import (
    CheckOutcome,
    TemplateClauseData,
    TemplateSourceData,
    run_all_checks,
)
from mbiu.corpus.pipeline.embed import (
    EmbeddingEngine,
    check_revision_compatibility,
    compute_clause_commonality,
)
from mbiu.corpus.pipeline.tag import (
    BaseClauseTagger,
    ClauseTags,
    DualTaggerConsensus,
    HeuristicClauseTagger,
    TaggingResult,
)

logger = logging.getLogger(__name__)


class CorpusPipelineError(Exception):
    """Base exception for corpus pipeline errors."""


class CorpusCheckFailureError(CorpusPipelineError):
    """Raised when one or more automated quality checks fail."""

    def __init__(self, message: str, check_outcomes: dict[str, CheckOutcome]) -> None:
        """Initialize error with check outcomes."""
        super().__init__(message)
        self.check_outcomes = check_outcomes


class CorpusVersionAlreadyExistsError(CorpusPipelineError):
    """Raised when attempting to publish a version tag that already exists."""


@dataclass(frozen=True)
class PublishResult:
    """Detailed result of a corpus version publish run."""

    version_tag: str
    published: bool
    is_active: bool
    total_sources: int
    total_chunks: int
    duplicates_removed: int
    check_outcomes: dict[str, CheckOutcome]
    published_at: datetime.datetime | None
    snapshot: CorpusSnapshot | None = None
    errors: list[str] = field(default_factory=list)


class CorpusPublisher:
    """Orchestrates candidate standard evaluation, embedding, and publishing."""

    def __init__(
        self,
        primary_tagger: BaseClauseTagger | None = None,
        secondary_tagger: BaseClauseTagger | None = None,
        embedding_engine: EmbeddingEngine | None = None,
    ) -> None:
        """Initialize publisher with tagging consensus and embedding engines."""
        self.primary_tagger = primary_tagger or HeuristicClauseTagger()
        self.secondary_tagger = secondary_tagger or HeuristicClauseTagger()
        self.consensus_evaluator = DualTaggerConsensus(
            primary_tagger=self.primary_tagger,
            secondary_tagger=self.secondary_tagger,
        )
        self.embedding_engine = embedding_engine or EmbeddingEngine()

    def publish_version(
        self,
        version_tag: str,
        sources: list[TemplateSourceData],
        clauses: list[TemplateClauseData],
        activate: bool = True,
        strict_checks: bool = True,
        dry_run: bool = False,
    ) -> PublishResult:
        """Execute the full pipeline and publish a new CorpusVersion.

        Steps:
        1. Ensure version tag does not already exist.
        2. Evaluate dual-tagging consensus.
        3. Run all six automated quality checks.
        4. If any check fails, abort and raise CorpusCheckFailureError (if strict).
        5. Generate 768-dim float32 unit embeddings.
        6. Compute clause commonality metrics.
        7. If dry_run is True, return PublishResult without writing to database.
        8. Atomically insert records and activate version.
        9. Reload in-memory snapshot.
        """
        # Step 1: Ensure version tag does not already exist
        if CorpusVersion.objects.filter(version_tag=version_tag).exists():
            raise CorpusVersionAlreadyExistsError(
                f"CorpusVersion '{version_tag}' already exists. Published versions are immutable."
            )

        # Step 2: Tagging and consensus
        tagging_results: list[TaggingResult] = []
        clause_tag_map: dict[str, ClauseTags] = {}

        for clause in clauses:
            src_ctx = {
                "contract_type": clause.source.contract_type,
                "jurisdiction": clause.source.jurisdiction,
            }
            res = self.consensus_evaluator.evaluate(
                text=clause.text,
                clause_key=clause.chunk_key,
                source_context=src_ctx,
            )
            tagging_results.append(res)
            if res.is_consensus and res.tags is not None:
                clause_tag_map[clause.chunk_key] = res.tags

        # Step 3: Run all six quality checks
        all_passed, check_outcomes, deduped_clauses = run_all_checks(
            sources=sources,
            clauses=clauses,
            tagging_results=tagging_results,
        )

        duplicates_removed = len(clauses) - len(deduped_clauses)

        # Step 4: Handle check failures
        if not all_passed:
            failed_checks = [k for k, v in check_outcomes.items() if not v.passed]
            error_msg = f"Corpus publication rejected. Quality checks failed: {failed_checks}"
            logger.error(error_msg)
            if strict_checks:
                raise CorpusCheckFailureError(error_msg, check_outcomes)
            return PublishResult(
                version_tag=version_tag,
                published=False,
                is_active=False,
                total_sources=len(sources),
                total_chunks=0,
                duplicates_removed=duplicates_removed,
                check_outcomes=check_outcomes,
                published_at=None,
                errors=[error_msg],
            )

        # Step 5: Embeddings
        # Verify active model revision compatibility
        active_version = CorpusVersion.objects.filter(is_active=True).first()
        if active_version is not None:
            check_revision_compatibility(
                existing_model_id=active_version.embedding_model_id,
                existing_dim=active_version.embedding_dim,
                new_model_id=self.embedding_engine.model_id,
                new_dim=self.embedding_engine.embedding_dim,
            )

        clauses_with_titles = [(c.source.title, c.text) for c in deduped_clauses]
        embeddings_matrix = self.embedding_engine.embed_clauses(clauses_with_titles)

        # Step 6: Compute pattern frequency / commonality
        commonality_metrics = compute_clause_commonality(embeddings_matrix)

        if dry_run:
            logger.info("Dry-run complete for %s. Database writes skipped.", version_tag)
            return PublishResult(
                version_tag=version_tag,
                published=False,
                is_active=False,
                total_sources=len(sources),
                total_chunks=len(deduped_clauses),
                duplicates_removed=duplicates_removed,
                check_outcomes=check_outcomes,
                published_at=None,
                snapshot=None,
            )

        # Step 7: Atomic Database Transaction
        published_timestamp = timezone.now()
        with transaction.atomic():
            # Create CorpusVersion
            version_obj = CorpusVersion.objects.create(
                version_tag=version_tag,
                is_active=False,
                embedding_model_id=self.embedding_engine.model_id,
                embedding_dim=self.embedding_engine.embedding_dim,
                published_at=published_timestamp,
            )

            # Record PipelineCheckResult records for all 6 checks
            for check_name, outcome in check_outcomes.items():
                PipelineCheckResult.objects.create(
                    corpus_version=version_obj,
                    check_name=check_name,
                    passed=outcome.passed,
                    details=outcome.details,
                )

            # Persist ReferenceSource records
            source_model_map: dict[str, ReferenceSource] = {}
            for src_data in sources:
                src_key = f"{src_data.title}::{src_data.jurisdiction}"
                source_obj, _ = ReferenceSource.objects.get_or_create(
                    title=src_data.title,
                    jurisdiction=src_data.jurisdiction,
                    defaults={
                        "url": src_data.url,
                        "license": src_data.license,
                        "reviewing_body": src_data.reviewing_body,
                        "contract_type": src_data.contract_type,
                    },
                )
                source_model_map[src_key] = source_obj

            # Prepare and bulk-create ReferenceChunk records
            chunks_to_create: list[ReferenceChunk] = []
            for i, clause in enumerate(deduped_clauses):
                tags = clause_tag_map.get(
                    clause.chunk_key,
                    ClauseTags(
                        contract_type=clause.source.contract_type,
                        topic="boilerplate",
                        jurisdiction=clause.source.jurisdiction,
                        drafted_for="neutral",
                    ),
                )
                src_key = f"{clause.source.title}::{clause.source.jurisdiction}"
                source_ref = source_model_map.get(src_key)

                combined_meta = dict(clause.metadata)
                if i < len(commonality_metrics):
                    combined_meta["commonality"] = commonality_metrics[i]

                chunk_obj = ReferenceChunk(
                    corpus_version=version_obj,
                    source=source_ref,
                    chunk_key=clause.chunk_key,
                    text=clause.text,
                    topic=tags.topic,
                    contract_type=tags.contract_type,
                    jurisdiction=tags.jurisdiction,
                    drafted_for=tags.drafted_for,
                    metadata=combined_meta,
                    embedding=embeddings_matrix[i].tolist(),
                )
                chunks_to_create.append(chunk_obj)

            ReferenceChunk.objects.bulk_create(chunks_to_create)

            # Atomically activate version if requested
            if activate:
                CorpusVersion.activate_version(version_tag)
                version_obj.refresh_from_db()

        # Step 8: Reload snapshot
        snapshot = load_corpus_snapshot() if activate else None

        return PublishResult(
            version_tag=version_tag,
            published=True,
            is_active=version_obj.is_active,
            total_sources=len(sources),
            total_chunks=len(chunks_to_create),
            duplicates_removed=duplicates_removed,
            check_outcomes=check_outcomes,
            published_at=published_timestamp,
            snapshot=snapshot,
        )
