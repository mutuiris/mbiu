"""Tests for the check, tag, embed and publish stage of the corpus pipeline.

Every document here is synthetic. The models, Presidio, Lingua and the embedder are
replaced with small fakes, so the tests need neither network nor the pipeline group.
"""

import hashlib
import json
import logging
import re
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
from pydantic import BaseModel

from mbiu.corpus.loader import active_snapshot, reset_snapshot
from mbiu.corpus.models import (
    CorpusVersion,
    PipelineCheckResult,
    ReferenceChunk,
    ReferenceSource,
)
from mbiu.corpus.snapshot import EMBEDDING_DIM
from mbiu.llm import ErrorCategory, LLMError, LLMResult
from mbiu.pipeline.checks import (
    check_english,
    check_metadata,
    check_near_duplicates,
    check_personal_data,
    check_standard_template,
    check_tag_agreement,
)
from mbiu.pipeline.cli import main
from mbiu.pipeline.embed import embed_clauses, embedding_text, pattern_counts
from mbiu.pipeline.errors import PipelineError
from mbiu.pipeline.models import DocumentOutcome, TemplateClause
from mbiu.pipeline.pipeline import read_clauses, write_clauses
from mbiu.pipeline.publish import PublishTools
from mbiu.pipeline.tag import ClauseTags, Tagger, chunk_key

RECORDING_SHA = "a" * 64
SIGNED_SHA = "b" * 64
SWAHILI_SHA = "c" * 64
SALES_SHA = "d" * 64

ROYALTY = (
    "The Label shall pay the Artist a royalty of fifteen percent of gross receipts "
    "from every sale or stream of the Masters, accounted for every six months."
)
AUDIT = (
    "The Artist may inspect and audit the books and records of the Label once in each "
    "calendar year on thirty days' written notice."
)
TERMINATION = (
    "Either party may end this Agreement on sixty days' written notice if the other party "
    "commits a material breach and does not remedy it within that period."
)
SIGNED_PARTIES = (
    "This Agreement is made between Amani Otieno of Example Street and Kilele Sounds "
    "Limited, and is signed by both of them today."
)
SWAHILI = (
    "Mkataba huu unaeleza malipo ya mrabaha kwa msanii kwa kila mauzo ya nyimbo zake "
    "katika kipindi cha miezi sita."
)
SALES_PAGE = (
    "Get our best-selling recording contract pack today and save twenty percent with the "
    "discount code at checkout."
)

DEFAULT_TAGS = ClauseTags(
    is_standard_template=True,
    contract_type="recording",
    topic="royalties",
    jurisdiction="KE",
    drafted_for="neutral",
)


def clause(
    text: str,
    clause_id: str = "1",
    *,
    sha: str = RECORDING_SHA,
    title: str | None = None,
    **overrides: Any,
) -> TemplateClause:
    fields: dict[str, Any] = {
        "clause_id": clause_id,
        "section": "main",
        "title": title,
        "text": text,
        "pages": [1],
        "source_url": f"https://example.org/templates/{sha[:4]}-recording-agreement.pdf",
        "contract_type": "recording",
        "jurisdiction": "KE",
        "licence": "CC BY 4.0",
        "reviewing_body": "Example Musicians' Union",
        "template_version": "1",
        "document_sha256": sha,
    }
    fields.update(overrides)
    return TemplateClause(**fields)


def keys(clauses: list[TemplateClause]) -> list[str]:
    return [chunk_key(c) for c in clauses]


class FakeModel:
    """Answers like a model adapter: default tags, changed where a phrase appears."""

    def __init__(self, provider: str, overrides: dict[str, dict[str, Any]] | None = None) -> None:
        self.provider = provider
        self.overrides = overrides or {}
        self.calls: list[dict[str, Any]] = []

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
        self.calls.append({"model": model, "instructions": instructions, "content": content})
        tags = DEFAULT_TAGS
        for phrase, changes in self.overrides.items():
            if phrase in content:
                tags = tags.model_copy(update=changes)
        return LLMResult(
            value=output.model_validate(tags.model_dump()),
            provider=self.provider,
            model_version=model,
            input_tokens=None,
            output_tokens=None,
        )


class FailingModel(FakeModel):
    async def generate[T: BaseModel](self, **kwargs: Any) -> LLMResult[T]:
        raise LLMError(ErrorCategory.UNAVAILABLE)


class FakeEmbedder:
    """Bag-of-words vectors: clauses that share words point the same way."""

    model_id = "gemini-embedding-2"
    revision = "synthetic-revision"

    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        vectors = np.zeros((len(texts), EMBEDDING_DIM), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"\w+", text.casefold()):
                digest = hashlib.blake2b(word.encode(), digest_size=4).digest()
                vectors[row, int.from_bytes(digest) % EMBEDDING_DIM] += 1.0
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


SYNTHETIC_NAMES = ("Amani Otieno",)


def fake_presidio(text: str) -> set[str]:
    return {"PERSON"} if any(name in text for name in SYNTHETIC_NAMES) else set()


def fake_lingua(text: str) -> bool:
    return "mkataba" not in text.casefold()


def tools(**changes: Any) -> PublishTools:
    defaults = PublishTools(
        taggers=[
            Tagger(FakeModel("gemini"), "gemini-test"),
            Tagger(FakeModel("openai"), "openai-test"),
        ],
        find_personal_data=fake_presidio,
        is_english=fake_lingua,
        embedder=FakeEmbedder(),
    )
    return replace(defaults, **changes)


@pytest.fixture(autouse=True)
def _restore_pipeline_logger() -> Iterator[None]:
    target = logging.getLogger("mbiu.pipeline")
    handlers, level, propagate = list(target.handlers), target.level, target.propagate
    yield
    target.handlers[:] = handlers
    target.setLevel(level)
    target.propagate = propagate


def test_metadata_check_drops_a_document_without_a_licence() -> None:
    good = [clause(ROYALTY)]
    unlicensed = [clause(AUDIT, sha=SIGNED_SHA, licence=" ", reviewing_body="")]

    kept, result = check_metadata(good + unlicensed)

    assert kept == good
    assert not result.passed
    assert result.details["checked"] == 2
    assert result.rejected == [
        {
            "document_sha256": SIGNED_SHA,
            "source_url": unlicensed[0].source_url,
            "reason": "missing: licence, reviewing_body",
        }
    ]


def test_personal_data_check_drops_a_signed_deal_and_never_records_the_name() -> None:
    template = [clause(ROYALTY), clause("Signed for [Artist Name] on ________.", "2")]
    signed = [clause(SIGNED_PARTIES, sha=SIGNED_SHA), clause(AUDIT, "2", sha=SIGNED_SHA)]
    seen: list[str] = []

    def finder(text: str) -> set[str]:
        seen.append(text)
        return fake_presidio(text)

    kept, result = check_personal_data(template + signed, finder)

    assert kept == template
    assert [r["document_sha256"] for r in result.rejected] == [SIGNED_SHA]
    assert result.rejected[0]["reason"] == "found: PERSON"
    assert "Amani" not in json.dumps(result.details)
    assert all("[Artist Name]" not in text and "____" not in text for text in seen)


def test_english_check_drops_a_swahili_document() -> None:
    english = [clause(ROYALTY), clause(AUDIT, "2")]
    swahili = [clause(SWAHILI, sha=SWAHILI_SHA)]

    kept, result = check_english(english + swahili, fake_lingua)

    assert kept == english
    assert [r["document_sha256"] for r in result.rejected] == [SWAHILI_SHA]


def test_near_duplicate_check_keeps_only_the_first_copy() -> None:
    original = clause(ROYALTY)
    copy = clause(ROYALTY.replace("months.", "months in arrears."), "1", sha=SIGNED_SHA)
    distinct = clause(AUDIT, "2")

    kept, result = check_near_duplicates([original, copy, distinct])

    assert kept == [original, distinct]
    assert len(result.rejected) == 1
    assert result.rejected[0]["chunk_key"] == chunk_key(copy)
    assert result.rejected[0]["reason"] == f"near-duplicate of {chunk_key(original)}"
    assert result.rejected[0]["similarity"] >= 0.85


def test_standard_template_check_drops_a_sales_page() -> None:
    template = [clause(ROYALTY)]
    sales = [clause(SALES_PAGE, sha=SALES_SHA)]
    votes = {
        chunk_key(template[0]): [DEFAULT_TAGS, DEFAULT_TAGS],
        chunk_key(sales[0]): [
            DEFAULT_TAGS,
            DEFAULT_TAGS.model_copy(update={"is_standard_template": False}),
        ],
    }

    kept, result = check_standard_template(template + sales, votes)

    assert kept == template
    assert [r["chunk_key"] for r in result.rejected] == keys(sales)


def test_tag_agreement_check_drops_clauses_the_models_disagree_on() -> None:
    agreed, disputed, single = clause(ROYALTY), clause(AUDIT, "2"), clause(TERMINATION, "3")
    votes = {
        chunk_key(agreed): [DEFAULT_TAGS, DEFAULT_TAGS.model_copy(update={"jurisdiction": "ke"})],
        chunk_key(disputed): [
            DEFAULT_TAGS,
            DEFAULT_TAGS.model_copy(update={"topic": "accounting_audit", "drafted_for": "artist"}),
        ],
        chunk_key(single): [DEFAULT_TAGS],
    }

    kept, result = check_tag_agreement([agreed, disputed, single], votes)

    assert kept == [agreed]
    assert result.rejected == [
        {"chunk_key": chunk_key(disputed), "reason": "models disagree on: topic, drafted_for"},
        {"chunk_key": chunk_key(single), "reason": "fewer than two models tagged it"},
    ]


def test_embedding_text_puts_the_heading_before_the_text() -> None:
    assert embedding_text(clause("Text.", title="Royalties")) == "Royalties\nText."
    assert embedding_text(clause("Text.")) == "Text."


@pytest.mark.parametrize(
    ("make", "message"),
    [
        (lambda n: np.zeros((n, EMBEDDING_DIM - 1), dtype=np.float32), "vectors"),
        (lambda n: np.full((n, EMBEDDING_DIM), np.nan, dtype=np.float32), "NaN"),
        (lambda n: np.ones((n, EMBEDDING_DIM), dtype=np.float32), "unit length"),
    ],
)
def test_embed_refuses_bad_vectors(
    make: Callable[[int], npt.NDArray[np.float32]], message: str
) -> None:
    class BadEmbedder(FakeEmbedder):
        def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
            return make(len(texts))

    with pytest.raises(PipelineError, match=message):
        embed_clauses([clause(ROYALTY)], BadEmbedder())


def test_pattern_counts_group_similar_clauses() -> None:
    texts = [ROYALTY, ROYALTY.replace("fifteen", "twenty"), TERMINATION]
    vectors = embed_clauses([clause(t, str(i)) for i, t in enumerate(texts)], FakeEmbedder())

    assert pattern_counts(vectors) == [2, 2, 1]


def test_read_clauses_round_trips_stage_one_output(tmp_path: Path) -> None:
    clauses = [clause(ROYALTY), clause(AUDIT, "2", title="Audit")]
    write_clauses(tmp_path, _outcome(clauses))

    assert read_clauses(tmp_path) == clauses


def test_read_clauses_fails_loudly_without_input(tmp_path: Path) -> None:
    with pytest.raises(PipelineError, match="no clause files"):
        read_clauses(tmp_path)

    (tmp_path / f"{'e' * 64}.jsonl").write_text('{"clause_id": "1"}\n', encoding="utf-8")
    with pytest.raises(PipelineError, match="line 1 is not a valid clause"):
        read_clauses(tmp_path)


@pytest.mark.django_db
class TestPublish:
    @pytest.fixture(autouse=True)
    def _fresh_snapshot(self) -> Iterator[None]:
        reset_snapshot()
        yield
        reset_snapshot()

    def write_documents(self, out: Path) -> None:
        documents = [
            [
                clause(ROYALTY, title="Royalties"),
                clause(AUDIT, "2"),
                clause(TERMINATION, "3"),
                clause(SALES_PAGE, "4"),
            ],
            [clause(SIGNED_PARTIES, sha=SIGNED_SHA), clause(AUDIT, "2", sha=SIGNED_SHA)],
            [clause(SWAHILI, sha=SWAHILI_SHA)],
            [clause(ROYALTY.replace("months.", "months in arrears."), sha=SALES_SHA)],
        ]
        for document in documents:
            write_clauses(out, _outcome(document))

    def test_publishes_only_checked_clauses_as_a_new_active_version(self, tmp_path: Path) -> None:
        self.write_documents(tmp_path)
        gemini = FakeModel("gemini", {"best-selling": {"is_standard_template": False}})
        openai = FakeModel("openai", {"material breach": {"topic": "termination"}})
        active_tools = tools(taggers=[Tagger(gemini, "gemini-test"), Tagger(openai, "openai-test")])

        code = main(
            ["publish", "--clauses", str(tmp_path), "--version-tag", "v1"],
            env={},
            tools=active_tools,
        )

        assert code == 0
        version = CorpusVersion.objects.get(version_tag="v1")
        assert version.is_active
        assert (version.embedding_model_id, version.embedding_revision) == (
            "gemini-embedding-2",
            "synthetic-revision",
        )
        chunks = list(version.chunks.order_by("chunk_key"))
        assert [c.text for c in chunks] == [ROYALTY, AUDIT]
        assert chunks[0].title == "Royalties"
        assert chunks[0].topic == "royalties"
        assert chunks[0].source.licence == "CC BY 4.0"
        assert chunks[0].source.title == "aaaa-recording-agreement"
        assert all(len(c.embedding) == EMBEDDING_DIM for c in chunks)

        results = {r.check_name: r for r in version.check_results.all()}
        assert {name: r.passed for name, r in results.items()} == {
            "metadata": True,
            "personal_data": False,
            "english": False,
            "near_duplicates": False,
            "standard_template": False,
            "tag_agreement": False,
        }
        assert "Amani" not in json.dumps([r.details for r in results.values()])

        # Each tagger saw only the clauses that survived the local checks
        assert len(gemini.calls) == len(openai.calls) == 4
        assert all("<template_clause" in call["content"] for call in gemini.calls)

        snapshot = active_snapshot()
        assert snapshot is not None
        assert snapshot.version_tag == "v1"
        assert [c.pattern_count for c in snapshot.chunks] == [1, 1]

    def test_a_new_version_leaves_the_old_one_untouched(self, tmp_path: Path) -> None:
        self.write_documents(tmp_path)
        assert (
            main(
                ["publish", "--clauses", str(tmp_path), "--version-tag", "v1"],
                env={},
                tools=tools(),
            )
            == 0
        )
        first = CorpusVersion.objects.get(version_tag="v1")
        first_chunks = list(first.chunks.values_list("id", "text"))

        class NewRevision(FakeEmbedder):
            revision = "newer-revision"

        code = main(
            ["publish", "--clauses", str(tmp_path), "--version-tag", "v2"],
            env={},
            tools=tools(embedder=NewRevision()),
        )

        assert code == 0
        first.refresh_from_db()
        assert not first.is_active
        assert list(first.chunks.values_list("id", "text")) == first_chunks
        second = CorpusVersion.objects.get(version_tag="v2")
        assert second.is_active
        assert second.embedding_revision == "newer-revision"
        assert ReferenceSource.objects.count() == 1

    def test_an_existing_tag_is_never_overwritten(self, tmp_path: Path) -> None:
        self.write_documents(tmp_path)
        assert (
            main(
                ["publish", "--clauses", str(tmp_path), "--version-tag", "v1"],
                env={},
                tools=tools(),
            )
            == 0
        )
        count = ReferenceChunk.objects.count()

        code = main(
            ["publish", "--clauses", str(tmp_path), "--version-tag", "v1"], env={}, tools=tools()
        )

        assert code == 1
        assert ReferenceChunk.objects.count() == count

    def test_nothing_is_published_when_every_clause_fails(self, tmp_path: Path) -> None:
        write_clauses(tmp_path, _outcome([clause(SWAHILI, sha=SWAHILI_SHA)]))

        code = main(
            ["publish", "--clauses", str(tmp_path), "--version-tag", "v1"], env={}, tools=tools()
        )

        assert code == 1
        assert not CorpusVersion.objects.exists()
        assert not PipelineCheckResult.objects.exists()

    def test_a_failed_model_call_stops_the_run(self, tmp_path: Path) -> None:
        self.write_documents(tmp_path)
        failing = tools(
            taggers=[
                Tagger(FakeModel("gemini"), "gemini-test"),
                Tagger(FailingModel("openai"), "openai-test"),
            ]
        )

        code = main(
            ["publish", "--clauses", str(tmp_path), "--version-tag", "v1"], env={}, tools=failing
        )

        assert code == 1
        assert not CorpusVersion.objects.exists()

    def test_missing_input_fails_loudly(self, tmp_path: Path) -> None:
        code = main(
            ["publish", "--clauses", str(tmp_path), "--version-tag", "v1"], env={}, tools=tools()
        )

        assert code == 1
        assert not CorpusVersion.objects.exists()


def _outcome(clauses: list[TemplateClause]) -> DocumentOutcome:
    sha = clauses[0].document_sha256
    return DocumentOutcome(
        source_url=clauses[0].source_url,
        document_url=clauses[0].source_url,
        sha256=sha,
        storage_key=f"raw/{sha}.pdf",
        created=True,
        rejected_reason=None,
        clauses=clauses,
    )
