"""
The API contract: every stream event, result and error the frontend receives.

These models are the source of truth. The frontend's TypeScript types and Zod schemas
are generated from them (`just types`), so this prevents having to write the same type
on either side.
"""

from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

SCHEMA_VERSION: Final = "1"

ClauseId = Annotated[str, Field(min_length=1, max_length=64)]
Page = Annotated[int, Field(ge=1)]


class Contract(BaseModel):
    """
    Base for every model: unknown fields are rejected, and fields with defaults are still
    marked required in generated types, because the server always sends them.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_serialization_defaults_required=True
    )


class Outcome(StrEnum):
    """How a clause compares with the reviewed standard."""

    MATCHES_STANDARD = "matches_standard"
    BETTER_FOR_YOU = "better_for_you"
    WORSE_FOR_YOU = "worse_for_you"
    NOT_IN_STANDARD = "not_in_standard"
    MISSING_FROM_CONTRACT = "missing_from_contract"
    CANNOT_COMPARE = "cannot_compare"


class ClauseStatus(StrEnum):
    """Whether a clause was checked, and with what result."""

    EVALUATED = "evaluated"
    CANNOT_COMPARE = "cannot_compare"
    EVALUATION_FAILED = "evaluation_failed"
    NOT_CHECKED = "not_checked"


class FailureReason(StrEnum):
    """Why a clause couldn't be checked; not_checked means the budget ran out first."""

    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    REFUSED = "refused"
    SCHEMA_INVALID = "schema_invalid"
    UNAVAILABLE = "unavailable"
    NOT_CHECKED = "not_checked"


class MoneyBasis(StrEnum):
    """Whether a percentage applies before costs (gross) or after them (net)."""

    GROSS = "gross"
    NET = "net"


class Provider(StrEnum):
    """The AI provider that produced a result."""

    GEMINI = "gemini"
    OPENAI = "openai"


class Stage(StrEnum):
    """A step of the evaluation, reported in progress events."""

    EXTRACT = "extract"
    SEGMENT = "segment"
    MAP = "map"
    RETRIEVE = "retrieve"
    COMPARE = "compare"
    VERIFY = "verify"
    SUMMARISE = "summarise"


# The document as Mbiu split it


class Section(Contract):
    """A part of the contract: the main body, a schedule or an annex."""

    section_id: str
    title: str | None
    kind: Literal["body", "schedule", "annex"]


class Clause(Contract):
    """One clause exactly as extracted, with its pages and character offsets."""

    clause_id: ClauseId
    section_id: str
    number: str | None = Field(description="As written in the contract, e.g. '7.2' or '(b)'")
    heading: str | None
    text: str = Field(description="Exact text as extracted, never rewritten")
    pages: list[Page] = Field(min_length=1)
    start: int = Field(ge=0, description="Character offset where the clause starts")
    end: int = Field(ge=0, description="Character offset just after the clause ends")


class SkippedPage(Contract):
    """A page Mbiu could not read, and why."""

    page: Page
    reason: Literal["no_text_layer", "not_english"]


class DocumentPayload(Contract):
    """The contract as Mbiu split it, sent before any checks finish."""

    page_count: int = Field(ge=1)
    sections: list[Section]
    clauses: list[Clause]
    skipped_pages: list[SkippedPage]


# The whole-contract map


class ClauseLink(Contract):
    """A link from one clause to another found in the contract map."""

    from_clause_id: ClauseId
    to_clause_id: ClauseId
    kind: Literal["cross_reference", "override", "defined_term", "same_topic"]


class ContractIssue(Contract):
    """
    Two clauses that contradict each other, or where one claims to override the other.
    Mbiu reports what each says; it never decides which one a court would apply.
    """

    kind: Literal["conflict", "override"]
    clause_ids: tuple[ClauseId, ClauseId]
    pages: list[Page] = Field(min_length=1)
    explanation: str
    quotes: tuple[str, str] = Field(description="Exact wording from each clause, in order")


class ContractMapPayload(Contract):
    """Links and contract-wide issues found by mapping the whole contract."""

    contract_type: str | None = Field(description="None when no reviewed standard covers it")
    links: list[ClauseLink]
    issues: list[ContractIssue]


# Per-clause results


class QuotedNumber(Contract):
    """A number with the exact contract wording it was read from."""

    value: float
    quote: str


class QuotedBasis(Contract):
    """A gross or net basis with the exact contract wording it was read from."""

    value: MoneyBasis
    quote: str


class QuotedText(Contract):
    """A value with the exact contract wording it was read from."""

    value: str
    quote: str


class ImpactInputs(Contract):
    """
    Inputs for the worked example in shillings. The frontend does the arithmetic; the
    model never does. Each value carries the exact wording it was read from.
    """

    royalty_rate_percent: QuotedNumber | None
    money_basis: QuotedBasis | None
    deductions: list[QuotedText]


class Evidence(Contract):
    """A reviewed template excerpt sent to the model for one clause."""

    evidence_id: str
    template_id: str
    source_title: str
    jurisdiction: str
    excerpt: str


class ClauseResult(Contract):
    """Everything one result card shows, already verified by code."""

    clause_id: ClauseId
    pages: list[Page] = Field(min_length=1)
    original_text: str
    status: ClauseStatus
    comparison: Outcome
    headline: str
    what_it_says: str
    what_it_means: str
    comparison_note: str | None
    impact_inputs: ImpactInputs | None
    linked_clauses: list[ClauseId]
    fairer_wording: str | None = Field(description="The template clause, unchanged")
    ask_them: str | None
    standard_template_id: str | None
    standard_excerpt: str | None
    evidence: list[Evidence]
    evidence_ids: list[str]
    evidence_quote: str | None
    provider: Provider | None
    model_version: str | None


class ClauseFailure(Contract):
    """A clause that couldn't be checked; retryable ones get a Retry button."""

    clause_id: ClauseId
    reason: FailureReason
    retryable: bool


class Progress(Contract):
    """How far the evaluation has got."""

    stage: Stage
    done: int = Field(ge=0)
    total: int = Field(ge=0)


# Summary


class Ask(Contract):
    """One question for the artist to put to the other party."""

    clause_id: ClauseId | None = Field(description="None for a missing protection")
    question: str


class MissingProtection(Contract):
    """A protection in the reviewed standard that the contract lacks."""

    template_id: str
    title: str
    excerpt: str
    ask_them: str


class ClauseNote(Contract):
    """A short note about one clause, such as good news."""

    clause_id: ClauseId
    text: str


class Versions(Contract):
    """Versions behind a report, so results can be traced and reproduced."""

    schema_version: str
    prompt: str
    model: str
    corpus: str


class Summary(Contract):
    """The end-of-evaluation summary, also used for the PDF report."""

    top_asks: list[Ask] = Field(max_length=3)
    contract_issues: list[ContractIssue]
    missing_protections: list[MissingProtection]
    good_news: list[ClauseNote]
    matches_count: int = Field(ge=0)
    skipped_pages: list[SkippedPage]
    ask_list: list[Ask]
    versions: Versions


# Stream events


class Heartbeat(Contract):
    """Empty payload sent every 10 seconds to keep the connection open."""


class DocumentEvent(Contract):
    """Sent once the contract is split into clauses."""

    type: Literal["document"] = "document"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: DocumentPayload


class ContractMapEvent(Contract):
    """Sent once the whole contract is mapped."""

    type: Literal["contract_map"] = "contract_map"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: ContractMapPayload


class ProgressEvent(Contract):
    """Sent as the evaluation moves through its stages."""

    type: Literal["progress"] = "progress"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: Progress


class ClauseResultEvent(Contract):
    """Sent when one clause's result is ready."""

    type: Literal["clause_result"] = "clause_result"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: ClauseResult


class ClauseUpdatedEvent(Contract):
    """Sent when a later finding changes a result already shown."""

    type: Literal["clause_updated"] = "clause_updated"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: ClauseResult


class ClauseFailedEvent(Contract):
    """Sent when one clause couldn't be checked."""

    type: Literal["clause_failed"] = "clause_failed"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: ClauseFailure


class HeartbeatEvent(Contract):
    """Sent every 10 seconds; carries nothing."""

    type: Literal["heartbeat"] = "heartbeat"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: Heartbeat


class DoneEvent(Contract):
    """Sent last, with the summary and ask list."""

    type: Literal["done"] = "done"
    schema_version: Literal["1"] = SCHEMA_VERSION
    payload: Summary


StreamEvent = Annotated[
    DocumentEvent
    | ContractMapEvent
    | ProgressEvent
    | ClauseResultEvent
    | ClauseUpdatedEvent
    | ClauseFailedEvent
    | HeartbeatEvent
    | DoneEvent,
    Field(discriminator="type"),
]
stream_event = TypeAdapter[StreamEvent](StreamEvent)


# Errors before the stream starts


class ErrorCode(StrEnum):
    """Why an upload was refused before the stream started."""

    INVALID_FILE_TYPE = "invalid_file_type"
    FILE_TOO_LARGE = "file_too_large"
    TOO_MANY_PAGES = "too_many_pages"
    ENCRYPTED_PDF = "encrypted_pdf"
    SCANNED_PDF = "scanned_pdf"
    MOSTLY_NOT_ENGLISH = "mostly_not_english"
    BOT_CHECK_FAILED = "bot_check_failed"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ApiError(Contract):
    """An error returned instead of a stream, with a message for the artist."""

    code: ErrorCode
    message: str = Field(description="Plain-language message to show the artist")
