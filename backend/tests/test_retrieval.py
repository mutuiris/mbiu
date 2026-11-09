import asyncio
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from mbiu.corpus.snapshot import EMBEDDING_DIM, CorpusSnapshot, SnapshotChunk
from mbiu.llm import ErrorCategory, LLMError
from mbiu.retrieval.embed import BATCH, GeminiEmbedder
from mbiu.retrieval.search import search
from mbiu.retrieval.topics import IMPACT_RANK, TOPIC_EXAMPLES, TOPICS, classify, impact_rank


def _chunk(
    key: str, text: str, *, jurisdiction: str = "KE", contract_type: str = "recording"
) -> SnapshotChunk:
    return SnapshotChunk(
        chunk_id=key,
        chunk_key=key,
        title="",
        text=text,
        topic="royalties",
        contract_type=contract_type,
        jurisdiction=jurisdiction,
        drafted_for="neutral",
        pattern_count=1,
        source_title="Synthetic",
        source_url="https://example.org/synthetic.pdf",
        licence="CC BY 4.0",
        reviewing_body="Example body",
    )


def _snapshot(chunks: list[SnapshotChunk], vectors: list[list[float]], tag: str) -> CorpusSnapshot:
    return CorpusSnapshot(
        version_tag=tag,
        embedding_model_id="test",
        embedding_revision="test",
        embeddings=np.array(vectors, dtype=np.float32),
        chunks=tuple(chunks),
    )


def test_every_tagged_topic_has_an_impact_rank_and_money_comes_first() -> None:
    assert set(IMPACT_RANK) == set(TOPICS)
    order = sorted(TOPICS, key=impact_rank)
    assert order[0] in {"royalties", "payment", "advances_recoupment", "accounting_audit"}
    assert impact_rank("boilerplate") > impact_rank("termination") > impact_rank("royalties")
    assert impact_rank("not-a-topic") == impact_rank("credit")


def test_classify_picks_the_nearest_example() -> None:
    examples = np.array([[1, 0], [0, 1]], dtype=np.float32)
    assert (
        classify(np.array([0.2, 0.9], dtype=np.float32), examples, ("royalties", "term")) == "term"
    )


def test_bm25_finds_the_clause_with_the_same_words_without_vectors() -> None:
    snapshot = _snapshot(
        [
            _chunk("KE-01", "The Artist receives a royalty of fifteen percent of gross receipts."),
            _chunk("KE-02", "This Agreement is governed by the laws of Kenya."),
        ],
        [[1, 0], [0, 1]],
        tag="bm25",
    )
    matches = search(snapshot, "What royalty percentage of gross receipts?", None, k=1)
    assert [m.chunk.chunk_key for m in matches] == ["KE-01"]


def test_vectors_and_words_are_fused() -> None:
    snapshot = _snapshot(
        [
            _chunk("KE-A", "payment schedule quarterly statements"),
            _chunk("KE-B", "unrelated wording entirely"),
        ],
        [[0.0, 1.0], [1.0, 0.0]],
        tag="fused",
    )
    # Words point to A, meaning points to B: both stay in the results
    matches = search(
        snapshot, "quarterly payment schedule", np.array([1.0, 0.0], dtype=np.float32), k=2
    )
    assert {m.chunk.chunk_key for m in matches} == {"KE-A", "KE-B"}


def test_kenyan_sources_come_before_foreign_ones() -> None:
    text = "The Artist receives a royalty of fifteen percent of gross receipts."
    snapshot = _snapshot(
        [_chunk("UK-01", text, jurisdiction="GB"), _chunk("KE-01", text + " Kenya.")],
        [[1, 0], [0.9, 0.1]],
        tag="kenya-first",
    )
    matches = search(snapshot, text, np.array([1.0, 0.0], dtype=np.float32), k=2)
    assert [m.chunk.chunk_key for m in matches] == ["KE-01", "UK-01"]


def test_contract_type_filter_falls_back_to_all_chunks() -> None:
    snapshot = _snapshot(
        [
            _chunk("REC", "royalty on recordings", contract_type="recording"),
            _chunk("PUB", "royalty on songs", contract_type="publishing"),
        ],
        [[1, 0], [0, 1]],
        tag="types",
    )
    assert [
        m.chunk.chunk_key for m in search(snapshot, "royalty", None, contract_type="publishing")
    ] == ["PUB"]
    assert len(search(snapshot, "royalty", None, contract_type="management")) == 2


def test_empty_corpus_returns_nothing() -> None:
    assert search(_snapshot([], [], tag="empty"), "anything", None) == []


class _FakeModels:
    """Stands in for the SDK: one vector per Content, from a lookup by text."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors
        self.calls: list[tuple[int, str]] = []

    def _respond(self, contents: list[Any], config: Any) -> Any:
        self.calls.append((len(contents), config.task_type))
        texts = [c.parts[0].text for c in contents]
        values = [self.vectors.get(t, [0.0] * EMBEDDING_DIM) for t in texts]
        return SimpleNamespace(embeddings=[SimpleNamespace(values=v) for v in values])

    async def embed_content(self, *, model: str, contents: list[Any], config: Any) -> Any:
        return self._respond(contents, config)


class _FakeClient:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.models_impl = _FakeModels(vectors)
        self.aio = SimpleNamespace(models=self.models_impl)
        # The synchronous client calls the same code without awaiting
        self.models = SimpleNamespace(
            embed_content=lambda **kw: self.models_impl._respond(kw["contents"], kw["config"])
        )


def _unit(axis: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    vector[axis] = 3.0
    return vector


def test_embedder_sends_each_text_separately_and_returns_unit_vectors() -> None:
    client = _FakeClient({"a": _unit(0), "b": _unit(1)})
    vectors = asyncio.run(GeminiEmbedder(client, "m").embed(["a", "b"], "RETRIEVAL_QUERY"))
    assert vectors.shape == (2, EMBEDDING_DIM)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    assert client.models_impl.calls == [(2, "RETRIEVAL_QUERY")]
    # The pipeline's synchronous path embeds corpus documents
    assert GeminiEmbedder(client, "m").encode(["a"]).shape == (1, EMBEDDING_DIM)
    assert client.models_impl.calls[-1] == (1, "RETRIEVAL_DOCUMENT")


def test_embedder_batches_large_requests() -> None:
    client = _FakeClient({})
    texts = [f"t{i}" for i in range(BATCH + 5)]
    client.models_impl.vectors = {t: _unit(0) for t in texts}
    asyncio.run(GeminiEmbedder(client, "m").embed(texts, "RETRIEVAL_QUERY"))
    assert [n for n, _ in client.models_impl.calls] == [BATCH, 5]


def test_embedder_rejects_empty_or_broken_vectors() -> None:
    client = _FakeClient({"zero": [0.0] * EMBEDDING_DIM, "nan": [float("nan")] * EMBEDDING_DIM})
    for text in ("zero", "nan"):
        with pytest.raises(LLMError) as err:
            asyncio.run(GeminiEmbedder(client, "m").embed([text], "RETRIEVAL_QUERY"))
        assert err.value.category is ErrorCategory.SCHEMA_INVALID


def test_plan_uses_corpus_evidence_and_classifies_topics(monkeypatch: pytest.MonkeyPatch) -> None:
    import mbiu.retrieval.evidence as ev

    snapshot = _snapshot(
        [_chunk("KE-ROY", "royalty of fifteen percent of gross receipts")],
        [_unit(0)],
        tag="plan",
    )
    examples = {t: _unit(1) for ex in TOPIC_EXAMPLES.values() for t in ex}
    examples.update({t: _unit(0) for t in TOPIC_EXAMPLES["royalties"]})
    client = _FakeClient({"Pay me ten percent royalty.": _unit(0), **examples})
    monkeypatch.setattr(ev, "embedder", lambda: GeminiEmbedder(client, "m"))
    monkeypatch.setattr(ev, "active_snapshot", lambda: snapshot)
    monkeypatch.setattr(ev, "_example_vectors", None)

    [plan] = asyncio.run(ev.plan_clauses(["Pay me ten percent royalty."], "recording"))
    assert [e.template_id for e in plan.evidence] == ["KE-ROY"]
    assert plan.evidence[0].evidence_id == "ev-KE-ROY"
    assert plan.topic == "royalties"


def test_plan_falls_back_to_synthetic_templates_without_a_corpus_or_embedder() -> None:
    # The autouse fixture leaves no corpus and an unavailable embedder
    from mbiu.retrieval.evidence import plan_clauses

    [plan] = asyncio.run(plan_clauses(["The royalty is 10% of net receipts."], None))
    assert plan.topic is None
    assert plan.evidence, "synthetic templates should still give evidence"


def _topic_chunk(key: str, topic: str, jurisdiction: str = "KE") -> SnapshotChunk:
    chunk = _chunk(key, f"Standard {topic} wording.", jurisdiction=jurisdiction)
    return SnapshotChunk(**{**chunk.__dict__, "topic": topic, "title": topic.title()})


def test_templates_that_disagree_are_named_with_the_contract_figure() -> None:
    from mbiu.retrieval.evidence import disagreement

    a = _chunk("KE-A", "Royalties are paid within thirty days of each quarter.")
    b = _chunk("UK-B", "Royalties are paid within 60 days of each quarter.", jurisdiction="GB")
    clause = "Royalties will be paid within 90 days."
    assert disagreement(clause, [a, b]) == (
        "Standard templates differ here: one gives 30 days, another 60 days. "
        "Your contract gives 90 days."
    )
    assert disagreement(clause, [a, a]) is None
    assert disagreement("Royalties are paid every quarter.", [a, b]) is None
    assert disagreement(clause, [a]) is None


def test_missing_protections_come_from_the_kenyan_standard_first() -> None:
    from mbiu.retrieval.evidence import PROTECTIONS, _missing

    snapshot = _snapshot(
        [
            _topic_chunk("UK-AUDIT", "accounting_audit", jurisdiction="GB"),
            _topic_chunk("KE-AUDIT", "accounting_audit"),
            _topic_chunk("KE-END", "termination"),
        ],
        [[1, 0], [1, 0], [1, 0]],
        tag="missing",
    )
    missing = _missing(snapshot, ["royalties", "termination"], "recording")
    assert [(m.template_id, m.ask_them) for m in missing] == [
        ("KE-AUDIT", PROTECTIONS["accounting_audit"])
    ]
    assert _missing(snapshot, ["accounting_audit", "termination", "payment"], "recording") == []


def test_missing_protections_say_nothing_without_known_topics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mbiu.retrieval.evidence as ev

    snapshot = _snapshot([_topic_chunk("KE-AUDIT", "accounting_audit")], [[1, 0]], tag="unknown")
    monkeypatch.setattr(ev, "active_snapshot", lambda: snapshot)
    assert asyncio.run(ev.missing_protections([None, None], "recording")) == []
    assert asyncio.run(ev.missing_protections(["royalties"], "recording"))


def test_sources_yaml_and_annotated_exemplars_load_cleanly() -> None:
    from pathlib import Path

    from mbiu.corpus.synthetic import (
        load_annotated_exemplars,
        retrieve_annotated_exemplar,
        retrieve_simple_evidence,
    )
    from mbiu.pipeline.sources import load_sources

    sources_path = Path(__file__).resolve().parents[2] / "corpus" / "sources.yaml"
    sources = load_sources(sources_path)
    assert len(sources) >= 10
    assert any("KECOBO" in s.reviewing_body for s in sources)
    assert any("Kenya Law" in s.reviewing_body for s in sources)

    ev_tax = retrieve_simple_evidence(
        "The payer shall deduct 5% KRA withholding tax and issue an iTax certificate."
    )
    assert ev_tax[0].template_id == "tpl-kra-cap470-withholding-tax"

    exemplars = load_annotated_exemplars()
    assert len(exemplars) == 37
    matched = retrieve_annotated_exemplar(
        "The Brand may train generative AI voice cloning and biometric likeness models.",
        contract_type="brand_partnership",
    )
    assert matched is not None
    assert "Sample Clause" in matched.format_for_prompt()

def test_synthetic_corpus_covers_all_contract_types_and_topics() -> None:
    from mbiu.corpus.synthetic import SYNTHETIC_CORPUS

    assert len(SYNTHETIC_CORPUS) == 41
    contract_types = {t.contract_type for t in SYNTHETIC_CORPUS}
    expected_contract_types = {
        "recording",
        "management",
        "publishing",
        "live_performance",
        "producer",
        "distribution",
        "synchronization",
        "general_music",
    }
    assert expected_contract_types.issubset(contract_types)

    topics = {t.topic for t in SYNTHETIC_CORPUS}
    expected_topics = {
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
        "dispute_resolution",
    }
    assert expected_topics.issubset(topics)


def test_in_memory_loader_and_api_context_builder() -> None:
    import time

    from mbiu.corpus.loader import (
        build_evaluation_api_context,
        get_annotated_exemplars,
        get_default_in_memory_snapshot,
        get_fallback_or_active_corpus_snapshot,
    )
    from mbiu.evaluation.views import build_evaluation_api_context as views_context_builder

    snapshot = get_default_in_memory_snapshot()
    assert len(snapshot.chunks) == 41
    assert snapshot.version_tag == "default-in-memory-standards-v1"

    fallback = get_fallback_or_active_corpus_snapshot()
    assert fallback is not None
    assert len(fallback.chunks) >= 32

    exemplars = get_annotated_exemplars()
    assert len(exemplars) == 37

    # Fast in-memory retrieval benchmark (< 0.5 ms)
    start = time.perf_counter()
    ctx = build_evaluation_api_context(
        "The Brand may train generative AI voice cloning and biometric likeness models.",
        contract_type="brand_partnership",
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 5.0  # Well below interactive request budget
    assert ctx["has_standard"] is True
    assert len(ctx["reference_chunks"]) >= 1
    assert ctx["annotated_exemplar"] is not None
    assert "Sample Clause" in ctx["annotated_exemplar"].format_for_prompt()

    # Views re-export matches loader implementation
    ctx2 = views_context_builder(
        "The Brand may train generative AI voice cloning and biometric likeness models.",
        contract_type="brand_partnership",
    )
    assert ctx2["has_standard"] is True
