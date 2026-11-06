"""Tag template clauses with two independent models through the storage-off adapters."""

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel

from mbiu.llm import LLMResult, as_data
from mbiu.pipeline.models import TemplateClause

PROMPT_PATH = Path(__file__).resolve().parents[1] / "llm" / "prompts" / "corpus_tag_v1.md"

ContractType = Literal[
    "recording",
    "publishing",
    "management",
    "distribution",
    "live_performance",
    "producer",
    "licensing",
    "assignment",
    "brand",
]
Topic = Literal[
    "royalties",
    "advances_recoupment",
    "payment",
    "grant_of_rights",
    "term",
    "exclusivity",
    "accounting_audit",
    "termination",
    "warranties_indemnities",
    "moral_rights",
    "credit",
    "governing_law",
    "dispute_resolution",
    "definitions",
    "boilerplate",
]
DraftedFor = Literal["label", "artist", "neutral"]


class ClauseTags(BaseModel):
    """One model's tags for one template clause."""

    is_standard_template: bool
    contract_type: ContractType
    topic: Topic
    jurisdiction: str
    drafted_for: DraftedFor


class StructuredModel(Protocol):
    """The shape shared by the Gemini and OpenAI adapters in ``mbiu.llm``."""

    provider: str

    async def generate[T: BaseModel](
        self,
        *,
        model: str,
        instructions: str,
        content: str,
        output: type[T],
        deadline: float,
        temperature: float = 0.1,
    ) -> LLMResult[T]:
        """Return validated JSON matching ``output``."""
        ...


@dataclass(frozen=True)
class Tagger:
    """A model adapter and the model name it should call."""

    llm: StructuredModel
    model: str


def chunk_key(clause: TemplateClause) -> str:
    """Readable ID for a clause, unique within a corpus version."""
    parts = (clause.jurisdiction, clause.contract_type, clause.document_sha256[:12])
    return "-".join(parts).upper() + f"-{clause.clause_id}"


async def tag_clauses(
    clauses: Sequence[TemplateClause],
    taggers: Sequence[Tagger],
    *,
    concurrency: int,
    timeout_s: float,
) -> dict[str, list[ClauseTags]]:
    """Ask every tagger about every clause and return the answers by chunk key.

    A failed call raises ``LLMError``: a run with missing votes must stop, not publish
    a smaller corpus.
    """
    instructions = PROMPT_PATH.read_text(encoding="utf-8")
    semaphore = asyncio.Semaphore(concurrency)

    async def ask(clause: TemplateClause, tagger: Tagger) -> ClauseTags:
        async with semaphore:
            result = await tagger.llm.generate(
                model=tagger.model,
                instructions=instructions,
                content=_content(clause),
                output=ClauseTags,
                deadline=time.monotonic() + timeout_s,
                temperature=0.0,
            )
        return result.value

    votes = await asyncio.gather(
        *(asyncio.gather(*(ask(clause, tagger) for tagger in taggers)) for clause in clauses)
    )
    return {chunk_key(c): list(v) for c, v in zip(clauses, votes, strict=True)}


def _content(clause: TemplateClause) -> str:
    text = f"{clause.title}\n{clause.text}" if clause.title else clause.text
    return as_data(
        "template_clause",
        text,
        contract_type=clause.contract_type,
        jurisdiction=clause.jurisdiction,
    )
