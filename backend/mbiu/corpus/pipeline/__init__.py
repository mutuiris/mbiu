"""Corpus pipeline package: tag, check, embed, and publish reference standards."""

from mbiu.corpus.pipeline.checks import (
    CheckOutcome,
    TemplateClauseData,
    TemplateSourceData,
    check_deduplication,
    check_language,
    check_tag_consensus,
    run_all_checks,
    scan_for_pii,
    validate_metadata,
    validate_template_nature,
)
from mbiu.corpus.pipeline.embed import (
    BaseEmbedder,
    DeterministicEmbedder,
    EmbeddingEngine,
    check_revision_compatibility,
    compute_clause_commonality,
    format_embedding_input,
    normalize_unit_length,
    validate_embedding_vector,
)
from mbiu.corpus.pipeline.publish import (
    CorpusCheckFailureError,
    CorpusPipelineError,
    CorpusPublisher,
    CorpusVersionAlreadyExistsError,
    PublishResult,
)
from mbiu.corpus.pipeline.runner import run_pipeline
from mbiu.corpus.pipeline.tag import (
    BaseClauseTagger,
    ClauseTags,
    DualTaggerConsensus,
    HeuristicClauseTagger,
    ModelClauseTagger,
    TaggingResult,
)

__all__ = [
    "BaseClauseTagger",
    "BaseEmbedder",
    "CheckOutcome",
    "ClauseTags",
    "CorpusCheckFailureError",
    "CorpusPipelineError",
    "CorpusPublisher",
    "CorpusVersionAlreadyExistsError",
    "DeterministicEmbedder",
    "DualTaggerConsensus",
    "EmbeddingEngine",
    "HeuristicClauseTagger",
    "ModelClauseTagger",
    "PublishResult",
    "TaggingResult",
    "TemplateClauseData",
    "TemplateSourceData",
    "check_deduplication",
    "check_language",
    "check_revision_compatibility",
    "check_tag_consensus",
    "compute_clause_commonality",
    "format_embedding_input",
    "normalize_unit_length",
    "run_all_checks",
    "run_pipeline",
    "scan_for_pii",
    "validate_embedding_vector",
    "validate_metadata",
    "validate_template_nature",
]
