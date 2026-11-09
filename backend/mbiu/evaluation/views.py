"""Evaluation API views and context builder handlers."""

from __future__ import annotations

from mbiu.api.views import clause_evaluations, evaluations
from mbiu.corpus.loader import (
    _find_relevant_annotated_exemplars,
    _find_relevant_reference_chunks,
    build_evaluation_api_context,
    get_annotated_exemplars,
    get_default_in_memory_snapshot,
    get_fallback_or_active_corpus_snapshot,
)

__all__ = [
    "evaluations",
    "clause_evaluations",
    "build_evaluation_api_context",
    "get_default_in_memory_snapshot",
    "get_fallback_or_active_corpus_snapshot",
    "get_annotated_exemplars",
    "_find_relevant_reference_chunks",
    "_find_relevant_annotated_exemplars",
]
