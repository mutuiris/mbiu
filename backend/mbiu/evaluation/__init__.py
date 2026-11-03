"""Mbiu evaluation package.

Provides clause evaluation, rule-based verification, repair orchestration,
comparison against reviewed reference standards, budgets & batching,
and consolidated evaluation summaries.
"""

from mbiu.evaluation.budgets import (
    AFFECTS_FREEDOM_TO_WORK,
    AFFECTS_MONEY,
    AFFECTS_OTHER,
    AFFECTS_OWNERSHIP,
    AFFECTS_TIME,
    EvaluationBudgetTracker,
    ImpactClassification,
    classify_clause_impact,
    create_clause_batches,
    order_clauses_by_impact,
    run_evaluation_batches,
)
from mbiu.evaluation.comparison import (
    NO_STANDARD_FOR_TYPE_MESSAGE,
    OUTCOME_BETTER_FOR_YOU,
    OUTCOME_CANNOT_COMPARE,
    OUTCOME_MATCHES_STANDARD,
    OUTCOME_MISSING_FROM_CONTRACT,
    OUTCOME_NOT_IN_STANDARD,
    OUTCOME_WORSE_FOR_YOU,
    STATUS_CANNOT_COMPARE,
    STATUS_EVALUATED,
    STATUS_EVALUATION_FAILED,
    STATUS_NOT_CHECKED,
    ClauseEvaluationResult,
    check_missing_protections,
    create_no_reviewed_standard_result,
    create_not_checked_result,
    evaluate_clause_with_verification,
    extract_fairer_wording,
    format_template_disagreement,
    validate_impact_inputs,
)
from mbiu.evaluation.summary import (
    EvaluationSummary,
    EvaluationVersions,
    generate_evaluation_summary,
    rank_top_asks,
)
from mbiu.evaluation.verify import (
    LABEL_CANNOT_COMPARE,
    LABEL_TYPICAL,
    LABEL_UNUSUAL,
    LABEL_WORTH_ASKING_ABOUT,
    ClauseProposal,
    EvaluationContext,
    EvidenceCitation,
    MoneyComparison,
    MoneyExampleInputs,
    repair_and_verify,
    verify_proposal,
)
from mbiu.evaluation.views import (
    clause_evaluations_view,
    generate_clause_evaluation_events,
)

__all__ = [
    # Budgets & batching
    "AFFECTS_FREEDOM_TO_WORK",
    "AFFECTS_MONEY",
    "AFFECTS_OTHER",
    "AFFECTS_OWNERSHIP",
    "AFFECTS_TIME",
    "EvaluationBudgetTracker",
    "ImpactClassification",
    "classify_clause_impact",
    "create_clause_batches",
    "order_clauses_by_impact",
    "run_evaluation_batches",
    # Comparison & reverse checks
    "ClauseEvaluationResult",
    "NO_STANDARD_FOR_TYPE_MESSAGE",
    "OUTCOME_BETTER_FOR_YOU",
    "OUTCOME_CANNOT_COMPARE",
    "OUTCOME_MATCHES_STANDARD",
    "OUTCOME_MISSING_FROM_CONTRACT",
    "OUTCOME_NOT_IN_STANDARD",
    "OUTCOME_WORSE_FOR_YOU",
    "STATUS_CANNOT_COMPARE",
    "STATUS_EVALUATED",
    "STATUS_EVALUATION_FAILED",
    "STATUS_NOT_CHECKED",
    "check_missing_protections",
    "create_no_reviewed_standard_result",
    "create_not_checked_result",
    "evaluate_clause_with_verification",
    "extract_fairer_wording",
    "format_template_disagreement",
    "validate_impact_inputs",
    # Summary
    "EvaluationSummary",
    "EvaluationVersions",
    "generate_evaluation_summary",
    "rank_top_asks",
    # Verify
    "LABEL_CANNOT_COMPARE",
    "LABEL_TYPICAL",
    "LABEL_UNUSUAL",
    "LABEL_WORTH_ASKING_ABOUT",
    "ClauseProposal",
    "EvaluationContext",
    "EvidenceCitation",
    "MoneyComparison",
    "MoneyExampleInputs",
    "repair_and_verify",
    "verify_proposal",
    # Views & events
    "clause_evaluations_view",
    "generate_clause_evaluation_events",
]
