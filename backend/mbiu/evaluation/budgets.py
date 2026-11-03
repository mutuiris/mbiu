"""Batching, concurrency, and budget enforcement engine for contract evaluation.

Enforces resource limits, concurrency controls, and impact-based prioritization
during contract evaluation:
- Impact Ordering: Money, ownership, term, exclusivity, and termination are evaluated
  first; operational and boilerplate clauses are evaluated last.
- Batching: Evaluates clauses in batches of 4-8 (default BATCH_SIZE=6).
- Concurrency: Limits concurrent LLM calls to LLM_CONCURRENCY (default 4).
- Budgets: Enforces per-batch time budget (BATCH_TIMEOUT_S=30s) and overall
  token budget per contract (TOKEN_BUDGET_PER_CONTRACT=400,000).
- Budget Exhaustion: Remaining lower-impact clauses are marked with status 'not_checked'
  and the kind artist message:
  "Mbiu checked the most important clauses first. N clauses aren't checked yet."

Zero Contract Storage Invariant:
All clause evaluation, batching, and tracking operate strictly in memory.
No contract text or clauses are ever persisted to disk, database, or external traces.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from django.conf import settings

T = TypeVar("T")

# ==============================================================================
# IMPACT ORDERING & TOPIC CLASSIFICATION
# ==============================================================================

# Priority scores (higher = evaluated earlier)
PRIORITY_MONEY = 100
PRIORITY_OWNERSHIP = 90
PRIORITY_TERM = 80
PRIORITY_EXCLUSIVITY = 70
PRIORITY_TERMINATION = 60
PRIORITY_CREDIT_DELIVERY = 50
PRIORITY_WARRANTIES_INDEMNITY = 40
PRIORITY_CONFIDENTIALITY = 35
PRIORITY_OTHER = 30
PRIORITY_DISPUTE_RESOLUTION = 25
PRIORITY_BOILERPLATE = 10

# Impacts on the artist's life/career: money, ownership, time, freedom_to_work, other
AFFECTS_MONEY = "money"
AFFECTS_OWNERSHIP = "ownership"
AFFECTS_TIME = "time"
AFFECTS_FREEDOM_TO_WORK = "freedom_to_work"
AFFECTS_OTHER = "other"


@dataclass(frozen=True)
class ImpactClassification:
    """Classification of a clause's topic, priority score, and career dimension."""

    topic: str
    priority_score: int
    affects: str


# Compiled regex patterns for topic classification
_MONEY_PATTERN = re.compile(
    r"\b(royalt\w*|advance\w*|recoup\w*|pay\w*|fee\w*|deduct\w*|commission\w*|"
    r"account\w*|audit\w*|net\s+receipts?|gross\s+receipts?|remunerat\w*|"
    r"compensat\w*|percent\w*|share\s+of|monies|money|income|revenue)\b",
    re.IGNORECASE,
)

_OWNERSHIP_PATTERN = re.compile(
    r"\b(masters?|copyrights?|intellectual\s+property|moral\s+rights?|publishing|"
    r"assign\w*|work\s+for\s+hire|grant\s+of\s+rights?|transfer\s+of\s+rights?|ownership|"
    r"title\s+and\s+interest|sound\s+recordings?|underlying\s+composition\w*|trademarks?|name\s+and\s+likeness)\b",
    re.IGNORECASE,
)

_TERM_PATTERN = re.compile(
    r"\b(terms?|duration\w*|periods?|renew\w*|exten\w*|post-term|option\s+periods?|"
    r"contract\s+periods?|effective\s+dates?|expir\w*|reversion\s+windows?)\b",
    re.IGNORECASE,
)

_EXCLUSIVITY_PATTERN = re.compile(
    r"\b(exclusiv\w*|sole\s+and\s+exclusive|restrict\w*|non-compete|non\s+compete|"
    r"right\s+of\s+first\s+refusal|rofr|lock-out|lock\s+out)\b",
    re.IGNORECASE,
)

_TERMINATION_PATTERN = re.compile(
    r"\b(terminat\w*|defaults?|breach\w*|cure\s+periods?|insolvency|material\s+breach|"
    r"cancell\w*|bankruptcy|right\s+to\s+terminate)\b",
    re.IGNORECASE,
)

_CREDIT_PATTERN = re.compile(
    r"\b(credits?|attribution|deliver\w*|acceptance|technical\s+specifications?|key\s+man|"
    r"artwork|deliverables?|release\s+commitments?)\b",
    re.IGNORECASE,
)

_WARRANTY_PATTERN = re.compile(
    r"\b(warrant\w*|represent\w*|indemn\w*|hold\s+harmless|liabilit\w*|"
    r"infring\w*|defense\s+of\s+claims?)\b",
    re.IGNORECASE,
)

_CONFIDENTIALITY_PATTERN = re.compile(
    r"\b(confidential\w*|non-disclosure|nondisclosure|trade\s+secrets?|proprietary\s+information)\b",
    re.IGNORECASE,
)

_DISPUTE_PATTERN = re.compile(
    r"\b(dispute\s+resolutions?|arbitrat\w*|mediat\w*|jurisdiction\s+clauses?|venue|legal\s+proceedings?)\b",
    re.IGNORECASE,
)

_BOILERPLATE_PATTERN = re.compile(
    r"\b(notices?|governing\s+laws?|jurisdictions?|severabilit\w*|entire\s+agreements?|"
    r"counterparts?|amendments?|waivers?|headings?|interpretations?|"
    r"force\s+majeure|signatures?|in\s+witness\s+whereof|recitals?)\b",
    re.IGNORECASE,
)


def classify_clause_impact(
    text: str,
    title: str | None = None,
    section: str | None = None,
) -> ImpactClassification:
    """Classify a clause by its topic, priority score, and career dimension.

    Args:
        text: Verbatim clause text.
        title: Optional clause title/heading.
        section: Optional section name (e.g. "main", "Signatures", "Boilerplate").

    Returns:
        ImpactClassification with topic, priority score (10-100), and affects dimension.
    """
    combined = f"{title or ''} {section or ''} {text}".strip()

    # Boilerplate sections check
    section_lower = (section or "").lower()
    if any(s in section_lower for s in ("signature", "recital", "notices")):
        return ImpactClassification("boilerplate", PRIORITY_BOILERPLATE, AFFECTS_OTHER)

    # 1. Money (highest priority)
    if _MONEY_PATTERN.search(combined):
        return ImpactClassification("money", PRIORITY_MONEY, AFFECTS_MONEY)

    # 2. Ownership
    if _OWNERSHIP_PATTERN.search(combined):
        return ImpactClassification("ownership", PRIORITY_OWNERSHIP, AFFECTS_OWNERSHIP)

    # 3. Term
    if _TERM_PATTERN.search(combined):
        return ImpactClassification("term", PRIORITY_TERM, AFFECTS_TIME)

    # 4. Exclusivity
    if _EXCLUSIVITY_PATTERN.search(combined):
        return ImpactClassification("exclusivity", PRIORITY_EXCLUSIVITY, AFFECTS_FREEDOM_TO_WORK)

    # 5. Termination
    if _TERMINATION_PATTERN.search(combined):
        return ImpactClassification("termination", PRIORITY_TERMINATION, AFFECTS_TIME)

    # 6. Credit & Delivery
    if _CREDIT_PATTERN.search(combined):
        return ImpactClassification("credit_delivery", PRIORITY_CREDIT_DELIVERY, AFFECTS_OTHER)

    # 7. Warranties & Indemnity
    if _WARRANTY_PATTERN.search(combined):
        return ImpactClassification(
            "warranties_indemnity", PRIORITY_WARRANTIES_INDEMNITY, AFFECTS_MONEY
        )

    # 8. Confidentiality
    if _CONFIDENTIALITY_PATTERN.search(combined):
        return ImpactClassification(
            "confidentiality", PRIORITY_CONFIDENTIALITY, AFFECTS_FREEDOM_TO_WORK
        )

    # 9. Dispute resolution
    if _DISPUTE_PATTERN.search(combined):
        return ImpactClassification(
            "dispute_resolution", PRIORITY_DISPUTE_RESOLUTION, AFFECTS_OTHER
        )

    # 10. Boilerplate
    if _BOILERPLATE_PATTERN.search(combined):
        return ImpactClassification("boilerplate", PRIORITY_BOILERPLATE, AFFECTS_OTHER)

    return ImpactClassification("other", PRIORITY_OTHER, AFFECTS_OTHER)


def order_clauses_by_impact[T](
    clauses: Sequence[T],
    text_extractor: Callable[[T], tuple[str, str | None, str | None]] | None = None,
) -> list[T]:
    """Sort clauses into impact order, maintaining relative order within identical tiers.

    Evaluation order:
    1. Money (royalties, advances, accounting, deductions)
    2. Ownership (masters, copyright, publishing, moral rights)
    3. Term (duration, options, renewals)
    4. Exclusivity (exclusive services, restrictions, ROFR)
    5. Termination (default, cure periods, cancellations)
    ...
    Last. Boilerplate (notices, governing law, signatures)

    Args:
        clauses: List or sequence of clause objects or dicts.
        text_extractor: Optional callable returning (text, title, section) from T.

    Returns:
        List of clauses ordered from highest to lowest impact.
    """
    if not clauses:
        return []

    def get_info(item: T) -> tuple[str, str | None, str | None]:
        if text_extractor is not None:
            return text_extractor(item)
        if isinstance(item, dict):
            return (
                str(item.get("text", "")),
                item.get("title"),
                item.get("section"),
            )
        # Duck typing on Clause dataclass or object
        text = getattr(item, "text", str(item))
        title = getattr(item, "title", None)
        section = getattr(item, "section", None)
        return (text, title, section)

    scored_items: list[tuple[int, int, T]] = []
    for idx, clause in enumerate(clauses):
        text, title, section = get_info(clause)
        classification = classify_clause_impact(text, title=title, section=section)
        # Sort descending by priority score, then ascending by original index (stable sort)
        scored_items.append((-classification.priority_score, idx, clause))

    scored_items.sort(key=lambda x: (x[0], x[1]))
    return [item[2] for item in scored_items]


# ==============================================================================
# BATCH CREATION (4 to 8 clauses per batch)
# ==============================================================================


def create_clause_batches[T](
    clauses: Sequence[T],
    batch_size: int | None = None,
    min_size: int = 4,
    max_size: int = 8,
) -> list[list[T]]:
    """Group clauses into balanced batches between min_size and max_size (4-8 clauses).

    Uses settings.BATCH_SIZE (default 6) clamped to [min_size, max_size].
    If total clauses <= max_size, a single batch is returned.
    If remaining items would leave an underfilled final batch (< min_size), items are
    redistributed across batches so all batches remain within [min_size, max_size]
    whenever mathematically possible.

    Args:
        clauses: Sequence of clauses to batch.
        batch_size: Target batch size (defaults to settings.BATCH_SIZE).
        min_size: Minimum allowable batch size (default 4).
        max_size: Maximum allowable batch size (default 8).

    Returns:
        List of clause batches.
    """
    items = list(clauses)
    total = len(items)
    if total == 0:
        return []
    if total <= max_size:
        return [items]

    configured_batch = batch_size if batch_size is not None else getattr(settings, "BATCH_SIZE", 6)
    target = max(min_size, min(max_size, configured_batch))

    # Calculate optimal number of batches
    # We want num_batches such that total / num_batches is between min_size and max_size
    num_batches = max(1, round(total / target))
    # Ensure num_batches does not violate constraints if possible
    while num_batches * max_size < total:
        num_batches += 1
    while num_batches * min_size > total and num_batches > 1:
        num_batches -= 1

    batches: list[list[T]] = []
    start = 0
    for i in range(num_batches):
        # Distribute items evenly
        remaining_items = total - start
        remaining_batches = num_batches - i
        size = remaining_items // remaining_batches
        if remaining_items % remaining_batches != 0:
            size += 1
        batches.append(items[start : start + size])
        start += size

    return batches


# ==============================================================================
# BUDGET TRACKER
# ==============================================================================


class EvaluationBudgetTracker:
    """Tracks token consumption and elapsed time against contract-level budgets.

    Attributes:
        clause_count: Total number of clauses in the evaluation request.
        token_budget: Total tokens allocated for this contract (default 400,000).
        batch_timeout_s: Per-batch execution timeout in seconds (default 30s).
        deadline_per_clause_s: Incremental time allowance per clause in seconds (default 3s).
        deadline_cap_s: Absolute ceiling on contract evaluation duration (default 300s).
    """

    def __init__(
        self,
        clause_count: int,
        token_budget: int | None = None,
        batch_timeout_s: float | None = None,
        deadline_per_clause_s: float | None = None,
        deadline_cap_s: float | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.clause_count = max(1, clause_count)
        self.token_budget = (
            token_budget
            if token_budget is not None
            else getattr(settings, "TOKEN_BUDGET_PER_CONTRACT", 400000)
        )
        self.batch_timeout_s = (
            batch_timeout_s
            if batch_timeout_s is not None
            else getattr(settings, "BATCH_TIMEOUT_S", 30.0)
        )
        self.deadline_per_clause_s = (
            deadline_per_clause_s
            if deadline_per_clause_s is not None
            else getattr(settings, "DEADLINE_PER_CLAUSE_S", 3.0)
        )
        self.deadline_cap_s = (
            deadline_cap_s
            if deadline_cap_s is not None
            else getattr(settings, "DEADLINE_CAP_S", 300.0)
        )

        self._clock = clock or time.monotonic
        self._start_time = self._clock()
        self._tokens_used = 0
        self._reserved_tokens = 0

        # Overall contract deadline grows with clause count, capped at deadline_cap_s
        computed_deadline = max(
            self.batch_timeout_s, self.clause_count * self.deadline_per_clause_s
        )
        self.overall_deadline_s = min(self.deadline_cap_s, computed_deadline)

    @property
    def tokens_used(self) -> int:
        """Total tokens consumed across all model calls for this contract."""
        return self._tokens_used

    @property
    def tokens_remaining(self) -> int:
        """Tokens remaining in this contract's budget."""
        return max(0, self.token_budget - self._tokens_used)

    @property
    def elapsed_seconds(self) -> float:
        """Seconds elapsed since evaluation began."""
        return self._clock() - self._start_time

    @property
    def time_remaining_s(self) -> float:
        """Seconds remaining before overall contract deadline is reached."""
        return max(0.0, self.overall_deadline_s - self.elapsed_seconds)

    @property
    def is_token_exhausted(self) -> bool:
        """True if the contract's token budget has been exhausted."""
        return self._tokens_used >= self.token_budget

    @property
    def is_time_exhausted(self) -> bool:
        """True if the overall evaluation deadline has been exceeded."""
        return self.elapsed_seconds >= self.overall_deadline_s

    def record_tokens(self, count: int) -> None:
        """Record tokens consumed by a model call.

        Args:
            count: Number of tokens used.
        """
        if count > 0:
            self._tokens_used += count

    def can_process_batch(self, estimated_tokens: int = 4000) -> bool:
        """Check whether budget allows processing another batch.

        Args:
            estimated_tokens: Expected token consumption for the candidate batch.

        Returns:
            True if sufficient tokens and time remain, False otherwise.
        """
        if self.is_token_exhausted or self.is_time_exhausted:
            return False
        # Do not start a batch if remaining time is less than
        # minimal execution threshold (e.g. 1.0s)
        if self.time_remaining_s < 1.0:
            return False
        return (self._tokens_used + self._reserved_tokens + estimated_tokens) <= self.token_budget

    def reserve_tokens(self, estimated_tokens: int = 4000) -> bool:
        """Reserve estimated tokens for an in-flight batch.

        Args:
            estimated_tokens: Anticipated token consumption.

        Returns:
            True if tokens were successfully reserved, False otherwise.
        """
        if self.can_process_batch(estimated_tokens):
            self._reserved_tokens += estimated_tokens
            return True
        return False

    def release_tokens(self, estimated_tokens: int = 4000) -> None:
        """Release previously reserved in-flight tokens.

        Args:
            estimated_tokens: Amount of tokens to release.
        """
        self._reserved_tokens = max(0, self._reserved_tokens - estimated_tokens)

    def get_not_checked_reason(self, remaining_clauses_count: int) -> str:
        """Generate the standard plain-language message for unchecked clauses.

        Invariant Message:
        "Mbiu checked the most important clauses first. N clauses aren't checked yet."

        Args:
            remaining_clauses_count: Number of clauses left unchecked.

        Returns:
            Artist-friendly notification string.
        """
        clause_str = "clause isn't" if remaining_clauses_count == 1 else "clauses aren't"
        return (
            f"Mbiu checked the most important clauses first. "
            f"{remaining_clauses_count} {clause_str} checked yet."
        )


# ==============================================================================
# ASYNC BATCH EXECUTION RUNNER
# ==============================================================================


async def run_evaluation_batches[T](
    batches: list[list[T]],
    batch_evaluator: Callable[[list[T]], Coroutine[Any, Any, tuple[list[Any], int]]],
    tracker: EvaluationBudgetTracker,
    concurrency_limit: int | None = None,
    on_not_checked: Callable[[list[T], str], list[Any]] | None = None,
) -> list[Any]:
    """Execute evaluation batches concurrently under limits and budget controls.

    Enforces:
    - settings.LLM_CONCURRENCY limit via concurrent worker tasks.
    - settings.BATCH_TIMEOUT_S via asyncio.wait_for per batch.
    - In-flight token reservations to prevent token budget over-subscription.
    - Budget Exhaustion handling: remaining clauses marked as not_checked.

    Args:
        batches: Pre-partitioned clause batches.
        batch_evaluator: Async callable taking a clause batch and returning (results, tokens_used).
        tracker: EvaluationBudgetTracker managing time and token limits.
        concurrency_limit: Max concurrent tasks (default settings.LLM_CONCURRENCY, 4).
        on_not_checked: Optional handler transforming unchecked clauses into result cards.

    Returns:
        Flattened list of all clause results (evaluated and not_checked) in batch order.
    """
    if not batches:
        return []

    concurrency = (
        concurrency_limit
        if concurrency_limit is not None
        else getattr(settings, "LLM_CONCURRENCY", 4)
    )
    worker_count = max(1, min(len(batches), concurrency))
    estimated_tokens = 4000

    queue: asyncio.Queue[tuple[int, list[T]]] = asyncio.Queue()
    for idx, batch in enumerate(batches):
        queue.put_nowait((idx, batch))

    results_by_index: dict[int, list[Any]] = {}
    budget_stopped = False
    lock = asyncio.Lock()

    async def worker() -> None:
        nonlocal budget_stopped
        while not queue.empty():
            async with lock:
                if budget_stopped:
                    break
                if not tracker.reserve_tokens(estimated_tokens):
                    budget_stopped = True
                    break
                try:
                    idx, batch = queue.get_nowait()
                except asyncio.QueueEmpty:
                    tracker.release_tokens(estimated_tokens)
                    break

            timeout_s = min(tracker.batch_timeout_s, tracker.time_remaining_s)
            try:
                results, tokens = await asyncio.wait_for(
                    batch_evaluator(batch),
                    timeout=max(0.5, timeout_s),
                )
                async with lock:
                    tracker.record_tokens(tokens)
                    tracker.release_tokens(estimated_tokens)
                    results_by_index[idx] = results
            except TimeoutError:
                reason = tracker.get_not_checked_reason(len(batch))
                async with lock:
                    tracker.release_tokens(estimated_tokens)
                    if on_not_checked is not None:
                        results_by_index[idx] = on_not_checked(batch, reason)
                    else:
                        results_by_index[idx] = []
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
    await asyncio.gather(*workers)

    # Handle any batches left unprocessed due to budget exhaustion
    unprocessed_indices = [i for i in range(len(batches)) if i not in results_by_index]
    if unprocessed_indices:
        remaining_items: list[T] = []
        for i in unprocessed_indices:
            remaining_items.extend(batches[i])
        reason = tracker.get_not_checked_reason(len(remaining_items))
        for i in unprocessed_indices:
            if on_not_checked is not None:
                results_by_index[i] = on_not_checked(batches[i], reason)
            else:
                results_by_index[i] = []

    all_results: list[Any] = []
    for i in range(len(batches)):
        all_results.extend(results_by_index.get(i, []))

    return all_results
