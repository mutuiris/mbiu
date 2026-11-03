"""Comprehensive test suite for the Mbiu corpus pipeline II.

Tests:
1. Automated quality checks:
   - Metadata validation (passing and failing fixtures)
   - Template validation (passing and failing fixtures)
   - PII / personal data scan (passing and failing fixtures)
   - Language check (English validation and foreign language rejection)
   - Deduplication check (MinHash / n-gram Jaccard near-duplicate removal)
   - Tag consensus check (dual-tagger agreement and disagreement handling)
2. Tagging module and dual-tagger consensus:
   - Topic detection, jurisdiction detection, perspective detection
3. Embedding module:
   - EmbeddingGemma 2 'title: {title} | text: {content}' format
   - Unit-length float32 vectors with exactly 768 dimensions
   - Commonality / pattern frequency calculation
   - Model revision and dimension incompatibility guards
4. End-to-end corpus release publishing:
   - Atomic database persistence of CorpusVersion, ReferenceChunk, PipelineCheckResult
   - Atomic version activation
   - In-memory snapshot synchronization
   - Rejection on quality check failure
   - Immutability of published releases
5. Non-negotiable Zero Contract Storage invariant:
   - Verification that user contracts and personal data are strictly excluded
"""

from collections.abc import Generator
from unittest.mock import MagicMock

import numpy as np
import pytest

from mbiu.corpus.loader import (
    clear_corpus_snapshot,
    get_active_corpus_snapshot,
    load_corpus_snapshot,
)
from mbiu.corpus.models import (
    CorpusVersion,
    PipelineCheckResult,
    ReferenceChunk,
)
from mbiu.corpus.pipeline.checks import (
    TemplateClauseData,
    TemplateSourceData,
    check_deduplication,
    check_language,
    check_tag_consensus,
    jaccard_similarity,
    scan_for_pii,
    validate_metadata,
    validate_template_nature,
)
from mbiu.corpus.pipeline.embed import (
    DEFAULT_EMBEDDING_DIM,
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
    CorpusPublisher,
    CorpusVersionAlreadyExistsError,
)
from mbiu.corpus.pipeline.runner import get_default_synthetic_standards, run_pipeline
from mbiu.corpus.pipeline.tag import (
    BaseClauseTagger,
    ClauseTags,
    DualTaggerConsensus,
    HeuristicClauseTagger,
    TaggingResult,
)


@pytest.fixture(autouse=True)
def _reset_snapshot_state() -> Generator[None]:
    """Clean snapshot before and after each test."""
    clear_corpus_snapshot()
    yield
    clear_corpus_snapshot()


# ==============================================================================
# 1. Automated Quality Checks Tests
# ==============================================================================


class TestQualityChecks:
    """Tests for all six automated pipeline quality checks."""

    def test_metadata_validation_success(self) -> None:
        """Valid source metadata with open license, reviewing body, and jurisdiction passes."""
        sources = [
            TemplateSourceData(
                title="WIPO Music Contract Guidance",
                license="CC BY 4.0",
                reviewing_body="WIPO",
                contract_type="management",
                jurisdiction="international",
            ),
            TemplateSourceData(
                title="Kenya Copyright Act Guidance",
                license="Kenya Copyright Act (Cap. 130)",
                reviewing_body="Kenya Copyright Board",
                contract_type="recording",
                jurisdiction="KE",
            ),
        ]
        outcome = validate_metadata(sources)
        assert outcome.passed is True
        assert outcome.details["invalid_count"] == 0

    def test_metadata_validation_missing_or_proprietary_license_fails(self) -> None:
        """Sources with missing, empty, or proprietary licenses are rejected."""
        sources = [
            TemplateSourceData(
                title="Proprietary Deal",
                license="All Rights Reserved",
                reviewing_body="Secret Label",
                contract_type="recording",
                jurisdiction="KE",
            ),
            TemplateSourceData(
                title="Unlicensed Deal",
                license="",
                reviewing_body="Unknown",
                contract_type="management",
                jurisdiction="KE",
            ),
        ]
        outcome = validate_metadata(sources)
        assert outcome.passed is False
        assert outcome.details["invalid_count"] == 2
        assert (
            "Unverified or proprietary license" in outcome.details["invalid_sources"][0]["errors"]
        )
        assert "Missing license" in outcome.details["invalid_sources"][1]["errors"]

    def test_metadata_validation_missing_reviewing_body_or_jurisdiction_fails(self) -> None:
        """Sources without reviewing body or jurisdiction are rejected."""
        sources = [
            TemplateSourceData(
                title="No Reviewer",
                license="CC0",
                reviewing_body="",
                contract_type="publishing",
                jurisdiction="",
            ),
        ]
        outcome = validate_metadata(sources)
        assert outcome.passed is False
        assert "Missing reviewing_body" in outcome.details["invalid_sources"][0]["errors"]
        assert "Missing jurisdiction" in outcome.details["invalid_sources"][0]["errors"]

    def test_metadata_validation_empty_sources_fails(self) -> None:
        """Empty sources list is rejected."""
        outcome = validate_metadata([])
        assert outcome.passed is False
        assert "No template sources provided" in outcome.details["error"]

    def test_template_validation_operative_clauses_pass(self) -> None:
        """Standard operative template clauses with legal placeholders pass validation."""
        source = TemplateSourceData(
            title="Standard Recording Agreement",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="recording",
            jurisdiction="KE",
        )
        clauses = [
            TemplateClauseData(
                chunk_key="REC-01",
                text="The Company shall pay to the Artist a royalty of 15% of Net Receipts.",
                source=source,
            ),
            TemplateClauseData(
                chunk_key="REC-02",
                text=(
                    "The Artist hereby grants to Company the exclusive right to "
                    "distribute recordings."
                ),
                source=source,
            ),
        ]
        outcome = validate_template_nature(clauses)
        assert outcome.passed is True
        assert outcome.details["invalid_count"] == 0

    def test_template_validation_signed_contract_fails(self) -> None:
        """Clauses containing executed signatures or witness execution dates are rejected."""
        source = TemplateSourceData(
            title="Executed Deal",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="recording",
        )
        clauses = [
            TemplateClauseData(
                chunk_key="SIGN-01",
                text=(
                    "In witness whereof the parties have executed this agreement on "
                    "14th March 2023."
                ),
                source=source,
            ),
        ]
        outcome = validate_template_nature(clauses)
        assert outcome.passed is False
        assert "signature block" in outcome.details["invalid_clauses"][0]["reasons"][0]

    def test_template_validation_marketing_and_blog_text_fails(self) -> None:
        """Promotional marketing text and blog post copy are rejected."""
        source = TemplateSourceData(
            title="Promo",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="recording",
        )
        clauses = [
            TemplateClauseData(
                chunk_key="PROMO-01",
                text=(
                    "Subscribe today and get a discount code for the best music "
                    "distribution platform!"
                ),
                source=source,
            ),
            TemplateClauseData(
                chunk_key="BLOG-01",
                text=(
                    "In this article we will explore how musicians can produce great sound tracks."
                ),
                source=source,
            ),
        ]
        outcome = validate_template_nature(clauses)
        assert outcome.passed is False
        assert outcome.details["invalid_count"] == 2

    def test_pii_scanner_clean_templates_pass(self) -> None:
        """Standard template placeholders ([Artist Name], Party A, Jane Doe) pass PII scan."""
        source = TemplateSourceData(
            title="Clean Source",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="management",
        )
        clauses = [
            TemplateClauseData(
                chunk_key="CLEAN-01",
                text="This Agreement is entered into by [Artist Name] and [Company Name], Party A.",
                source=source,
            ),
            TemplateClauseData(
                chunk_key="CLEAN-02",
                text="Notices may be sent to contact@example.com or info@wipo.int.",
                source=source,
            ),
        ]
        outcome = scan_for_pii(clauses)
        assert outcome.passed is True
        assert outcome.details["violations_count"] == 0

    def test_pii_scanner_real_email_fails(self) -> None:
        """Real personal email addresses in template candidates are rejected."""
        source = TemplateSourceData(
            title="Source", license="CC BY 4.0", reviewing_body="WIPO", contract_type="recording"
        )
        clauses = [
            TemplateClauseData(
                chunk_key="EMAIL-01",
                text="Send accounting statements to artist.personal99@gmail.com immediately.",
                source=source,
            ),
        ]
        outcome = scan_for_pii(clauses)
        assert outcome.passed is False
        assert outcome.details["violations_count"] == 1
        assert outcome.details["violations"][0]["type"] == "email"

    def test_pii_scanner_phone_numbers_and_addresses_fail(self) -> None:
        """Real phone numbers, street addresses, and national ID numbers are rejected."""
        source = TemplateSourceData(
            title="Source", license="CC BY 4.0", reviewing_body="WIPO", contract_type="recording"
        )
        clauses = [
            TemplateClauseData(
                chunk_key="PHONE-01",
                text="The Artist may be contacted at +254 712 345678 for performance booking.",
                source=source,
            ),
            TemplateClauseData(
                chunk_key="ADDR-01",
                text="Physical address: 124 Kenyatta Avenue, Nairobi for legal service of process.",
                source=source,
            ),
            TemplateClauseData(
                chunk_key="ID-01",
                text="Artist National ID: 29847162 registered under the laws of Kenya.",
                source=source,
            ),
        ]
        outcome = scan_for_pii(clauses)
        assert outcome.passed is False
        assert outcome.details["violations_count"] == 3
        v_types = {v["type"] for v in outcome.details["violations"]}
        assert "kenyan_phone_number" in v_types
        assert "street_address" in v_types
        assert "national_id_or_passport" in v_types

    def test_language_check_english_passes(self) -> None:
        """English standard clauses pass language verification."""
        source = TemplateSourceData(
            title="English Template",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="management",
        )
        clauses = [
            TemplateClauseData(
                chunk_key="LANG-01",
                text=(
                    "The Manager shall render true and accurate written monthly "
                    "accounting statements."
                ),
                source=source,
            ),
        ]
        outcome = check_language(clauses)
        assert outcome.passed is True
        assert outcome.details["non_english_count"] == 0

    def test_language_check_non_english_fails(self) -> None:
        """Non-English clauses (Swahili, French, German) are rejected."""
        source = TemplateSourceData(
            title="Foreign Source",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="recording",
        )
        clauses = [
            TemplateClauseData(
                chunk_key="SWAHILI-01",
                text="Mkataba huu unaweka masharti ya usimamizi wa muziki na fedha zote za msanii.",
                source=source,
            ),
            TemplateClauseData(
                chunk_key="FRENCH-01",
                text=(
                    "Le présent contrat régit les relations professionnelles "
                    "entre l'artiste et la société."
                ),
                source=source,
            ),
        ]
        outcome = check_language(clauses)
        assert outcome.passed is False
        assert outcome.details["non_english_count"] == 2

    def test_deduplication_exact_and_near_duplicates_removed(self) -> None:
        """Near-duplicate clauses are detected and deduplicated via n-gram Jaccard."""
        source = TemplateSourceData(
            title="Dedup Source",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="recording",
        )
        c1 = TemplateClauseData(
            chunk_key="ORIGINAL-01",
            text="The Company shall pay the Artist a royalty of 15% of Net Receipts.",
            source=source,
        )
        # c2 is nearly identical with minor whitespace / token addition
        c2 = TemplateClauseData(
            chunk_key="DUPLICATE-01",
            text="The Company shall pay the Artist a royalty of 15% of Net Receipts hereunder.",
            source=source,
        )
        c3 = TemplateClauseData(
            chunk_key="DISTINCT-01",
            text=(
                "The Artist grants an exclusive option to extend the Term "
                "for two additional periods."
            ),
            source=source,
        )

        outcome, deduped = check_deduplication([c1, c2, c3], similarity_threshold=0.70)
        assert outcome.passed is True
        assert outcome.details["duplicates_removed"] == 1
        assert len(deduped) == 2
        assert deduped[0].chunk_key == "ORIGINAL-01"
        assert deduped[1].chunk_key == "DISTINCT-01"

    def test_jaccard_similarity_calculation(self) -> None:
        """Test Jaccard metric behavior on identical, disjoint, and overlapping sets."""
        s1 = {"a", "b", "c"}
        s2 = {"a", "b", "c"}
        s3 = {"d", "e"}
        s4 = {"b", "c", "d"}

        assert jaccard_similarity(s1, s2) == 1.0
        assert jaccard_similarity(s1, s3) == 0.0
        assert round(jaccard_similarity(s1, s4), 3) == 0.500

    def test_tag_consensus_check_agreement_and_disagreement(self) -> None:
        """Consensus check passes on full agreement and records failures on disagreement."""
        tags_a = ClauseTags(
            contract_type="recording",
            topic="royalties",
            jurisdiction="KE",
            drafted_for="neutral",
        )
        tags_b = ClauseTags(
            contract_type="recording",
            topic="accounting_audit",  # Disagrees on topic
            jurisdiction="KE",
            drafted_for="neutral",
        )

        agreed_res = TaggingResult(
            clause_key="KEY-01",
            text="text",
            tags=tags_a,
            primary_tags=tags_a,
            secondary_tags=tags_a,
            is_consensus=True,
        )
        disagreed_res = TaggingResult(
            clause_key="KEY-02",
            text="text",
            tags=None,
            primary_tags=tags_a,
            secondary_tags=tags_b,
            is_consensus=False,
            disagreements={"topic": ("royalties", "accounting_audit")},
        )

        # All agreed passes
        pass_outcome = check_tag_consensus([agreed_res])
        assert pass_outcome.passed is True
        assert pass_outcome.details["disagreements_count"] == 0

        # Disagreement fails
        fail_outcome = check_tag_consensus([agreed_res, disagreed_res])
        assert fail_outcome.passed is False
        assert fail_outcome.details["disagreements_count"] == 1
        assert fail_outcome.details["disagreements"][0]["clause_key"] == "KEY-02"


# ==============================================================================
# 2. Tagging Module and Dual-Tagger Consensus Tests
# ==============================================================================


class TestTaggingAndConsensus:
    """Tests for heuristic tagger and dual-tagger consensus."""

    def test_heuristic_topic_detection(self) -> None:
        """Heuristic tagger identifies legal topics from music industry keywords."""
        tagger = HeuristicClauseTagger(default_jurisdiction="KE")

        assert (
            tagger.tag_clause("The artist receives 18% of net receipts", "Clause 4").topic
            == "royalties"
        )
        assert (
            tagger.tag_clause("Advances of KES 200,000 shall be recoupable from royalties").topic
            == "advances_recoupment"
        )
        assert (
            tagger.tag_clause("Artist hereby grants exclusive recording rights").topic
            == "exclusivity"
        )
        assert (
            tagger.tag_clause("Initial period of one year with two option periods").topic
            == "term_duration"
        )
        assert (
            tagger.tag_clause("Right to inspect and audit books of account annually").topic
            == "accounting_audit"
        )
        assert (
            tagger.tag_clause("Either party may terminate upon 30 days written notice").topic
            == "termination"
        )
        assert (
            tagger.tag_clause("Artist retains all moral rights and paternity over works").topic
            == "moral_rights"
        )
        assert (
            tagger.tag_clause("Governed by the laws of Kenya and High Court jurisdiction").topic
            == "governing_law_jurisdiction"
        )
        assert (
            tagger.tag_clause("Any dispute shall be referred to arbitration in Nairobi").topic
            == "dispute_resolution"
        )

    def test_heuristic_drafted_for_detection(self) -> None:
        """Heuristic tagger detects whether a clause favors label, artist, or neutral standard."""
        tagger = HeuristicClauseTagger()

        # Favour label
        label_clause = "Record Company in its sole discretion may cross-collateralize all earnings"
        assert tagger.tag_clause(label_clause).drafted_for == "label"

        # Favour artist
        artist_clause = (
            "Subject to artist's prior written consent and rights shall revert to artist"
        )
        assert tagger.tag_clause(artist_clause).drafted_for == "artist"

        # Neutral standard
        neutral_clause = "Statements shall be rendered semi-annually within sixty days"
        assert tagger.tag_clause(neutral_clause).drafted_for == "neutral"

    def test_dual_tagger_consensus_success(self) -> None:
        """Dual tagger consensus is achieved when both taggers agree on all four attributes."""
        primary = HeuristicClauseTagger()
        secondary = HeuristicClauseTagger()
        evaluator = DualTaggerConsensus(primary, secondary)

        text = "The Company shall pay royalties of 15% of gross receipts"
        res = evaluator.evaluate(text, "ROY-01", {"contract_type": "recording"})

        assert res.is_consensus is True
        assert res.tags is not None
        assert res.tags.topic == "royalties"
        assert res.tags.contract_type == "recording"
        assert len(res.disagreements) == 0

    def test_dual_tagger_consensus_disagreement_rejection(self) -> None:
        """Dual tagger rejects tags when taggers disagree on any field."""
        primary = HeuristicClauseTagger()

        # Custom mock secondary tagger that disagrees on drafted_for
        mock_secondary = MagicMock(spec=BaseClauseTagger)
        mock_secondary.tag_clause.return_value = ClauseTags(
            contract_type="recording",
            topic="royalties",
            jurisdiction="KE",
            drafted_for="label",  # Disagrees with primary's "neutral"
        )

        evaluator = DualTaggerConsensus(primary, mock_secondary)
        text = "Royalties shall be paid at 15% of gross receipts"
        res = evaluator.evaluate(text, "ROY-02", {"contract_type": "recording"})

        assert res.is_consensus is False
        assert res.tags is None
        assert "drafted_for" in res.disagreements


# ==============================================================================
# 3. Embedding Module Tests
# ==============================================================================


class TestEmbeddingModule:
    """Tests for vector embedding generation, EmbeddingGemma 2 spec, and commonality."""

    def test_embedding_input_format_spec(self) -> None:
        """Title and text formatting strictly follows EmbeddingGemma 2 specification."""
        title = "WIPO Management Annex A"
        content = "The manager receives 15% commission."
        formatted = format_embedding_input(title, content)
        assert (
            formatted
            == "title: WIPO Management Annex A | text: The manager receives 15% commission."
        )

    def test_embedding_vector_dimensions_and_unit_norm(self) -> None:
        """Embeddings have 768 float32 dimensions and exact unit L2 norm."""
        engine = EmbeddingEngine(embedder=DeterministicEmbedder())
        assert engine.embedding_dim == DEFAULT_EMBEDDING_DIM

        clauses = [
            ("Annex A", "Clause text 1"),
            ("Annex B", "Clause text 2"),
        ]
        embeddings = engine.embed_clauses(clauses)

        assert embeddings.shape == (2, 768)
        assert embeddings.dtype == np.float32

        # Check unit norm for each vector
        for vec in embeddings:
            validate_embedding_vector(vec, expected_dim=768)
            norm = float(np.linalg.norm(vec))
            assert abs(norm - 1.0) < 1e-4

    def test_normalize_unit_length_handles_zero_vector(self) -> None:
        """Zero vector normalization safely avoids division by zero."""
        zero_vec = np.zeros(768, dtype=np.float32)
        norm_vec = normalize_unit_length(zero_vec)
        assert np.array_equal(norm_vec, zero_vec)

    def test_compute_clause_commonality_grouping(self) -> None:
        """Cosine similarity matrix groups similar clauses to calculate commonality score."""
        # Create 3 vectors: vec1 and vec2 nearly identical, vec3 orthogonal
        v1 = np.zeros(768, dtype=np.float32)
        v1[0] = 1.0

        v2 = np.zeros(768, dtype=np.float32)
        v2[0] = 0.99
        v2[1] = 0.14
        v2 = normalize_unit_length(v2)

        v3 = np.zeros(768, dtype=np.float32)
        v3[2] = 1.0

        embeddings = np.vstack([v1, v2, v3])
        metrics = compute_clause_commonality(embeddings, similarity_threshold=0.85)

        assert len(metrics) == 3
        # v1 and v2 match each other (cluster size = 2)
        assert metrics[0]["cluster_size"] == 2
        assert metrics[0]["is_common_pattern"] is True
        assert metrics[1]["cluster_size"] == 2
        assert metrics[1]["is_common_pattern"] is True

        # v3 matches only itself (cluster size = 1)
        assert metrics[2]["cluster_size"] == 1
        assert metrics[2]["is_common_pattern"] is False

    def test_check_revision_compatibility_guards(self) -> None:
        """Attempting to mix different embedding models or dimensions raises ValueError."""
        # Compatible
        check_revision_compatibility("google/embeddinggemma-2", 768, "google/embeddinggemma-2", 768)

        # Incompatible model ID
        with pytest.raises(ValueError, match="Embedding model mismatch"):
            check_revision_compatibility(
                "google/embeddinggemma-2", 768, "openai/text-embedding-3", 768
            )

        # Incompatible dimension
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            check_revision_compatibility(
                "google/embeddinggemma-2", 768, "google/embeddinggemma-2", 1536
            )


# ==============================================================================
# 4. End-to-End Publishing & Database Verification Tests
# ==============================================================================


@pytest.mark.django_db
class TestCorpusPublishingE2E:
    """End-to-end integration tests for publishing and activating corpus versions."""

    def test_end_to_end_publish_and_activate(self) -> None:
        """Publishing valid standards creates version, chunks, checks, and activates in memory."""
        sources, clauses = get_default_synthetic_standards()

        publisher = CorpusPublisher()
        result = publisher.publish_version(
            version_tag="v1.0.0-release",
            sources=sources,
            clauses=clauses,
            activate=True,
            strict_checks=True,
        )

        assert result.published is True
        assert result.is_active is True
        assert result.version_tag == "v1.0.0-release"
        assert result.total_chunks == len(clauses)
        assert result.published_at is not None

        # Verify CorpusVersion in database
        cv = CorpusVersion.objects.get(version_tag="v1.0.0-release")
        assert cv.is_active is True
        assert cv.embedding_model_id == "google/embeddinggemma-2"
        assert cv.embedding_dim == 768

        # Verify all 6 PipelineCheckResult records in database
        check_results = list(PipelineCheckResult.objects.filter(corpus_version=cv))
        assert len(check_results) == 6
        assert all(c.passed for c in check_results)
        check_names = {c.check_name for c in check_results}
        assert check_names == {
            "metadata_validation",
            "template_validation",
            "pii_scan",
            "language_check",
            "deduplication",
            "tag_consensus",
        }

        # Verify ReferenceChunk rows in database
        chunks = list(ReferenceChunk.objects.filter(corpus_version=cv))
        assert len(chunks) == len(clauses)
        for chunk in chunks:
            assert chunk.source is not None
            assert chunk.topic in [
                "royalties",
                "accounting_audit",
                "moral_rights",
                "advances_recoupment",
                "boilerplate",
            ]
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 768

        # Verify in-memory snapshot was updated
        snapshot = get_active_corpus_snapshot()
        assert snapshot is not None
        assert snapshot.version_tag == "v1.0.0-release"
        assert snapshot.total_chunks == len(clauses)
        assert snapshot.embeddings.shape == (len(clauses), 768)
        assert snapshot.embeddings.dtype == np.float32

    def test_publish_rejection_on_pii_check_failure(self) -> None:
        """Candidate standard containing personal data aborts publication."""
        sources, clauses = get_default_synthetic_standards()

        # Poison one clause with real personal email
        poisoned_clauses = list(clauses) + [
            TemplateClauseData(
                chunk_key="POISON-01",
                text="The artist personal email is leaked.artist@gmail.com for correspondence.",
                source=sources[0],
            ),
        ]

        publisher = CorpusPublisher()
        with pytest.raises(CorpusCheckFailureError) as exc_info:
            publisher.publish_version(
                version_tag="v1.0.0-fail",
                sources=sources,
                clauses=poisoned_clauses,
                activate=True,
                strict_checks=True,
            )

        assert "pii_scan" in str(exc_info.value)
        # Verify no version was published or activated
        assert not CorpusVersion.objects.filter(version_tag="v1.0.0-fail").exists()

    def test_publish_rejection_on_unverified_license(self) -> None:
        """Candidate standard with unverified proprietary license aborts publication."""
        sources = [
            TemplateSourceData(
                title="Proprietary Source",
                license="All Rights Reserved",
                reviewing_body="Unknown",
                contract_type="recording",
            ),
        ]
        clauses = [
            TemplateClauseData(
                chunk_key="P-01",
                text="The company shall pay royalties of 10% to the artist.",
                source=sources[0],
            ),
        ]

        publisher = CorpusPublisher()
        with pytest.raises(CorpusCheckFailureError):
            publisher.publish_version(
                version_tag="v1.0.0-bad-lic",
                sources=sources,
                clauses=clauses,
                strict_checks=True,
            )

    def test_version_tag_immutability_duplicate_tag_rejected(self) -> None:
        """Attempting to publish an existing version tag raises CorpusVersionAlreadyExistsError."""
        sources, clauses = get_default_synthetic_standards()
        publisher = CorpusPublisher()

        # First publish
        publisher.publish_version(
            version_tag="v1.0.0-immutable",
            sources=sources,
            clauses=clauses,
            activate=True,
        )

        # Attempt to publish under same tag again
        with pytest.raises(CorpusVersionAlreadyExistsError):
            publisher.publish_version(
                version_tag="v1.0.0-immutable",
                sources=sources,
                clauses=clauses,
            )

    def test_run_pipeline_cli_runner_dry_run(self) -> None:
        """CLI runner dry-run validates standards without touching the database."""
        result = run_pipeline(
            version_tag="v1.0.0-cli-dry",
            dry_run=True,
        )
        assert result.published is False
        assert result.is_active is False
        assert not CorpusVersion.objects.filter(version_tag="v1.0.0-cli-dry").exists()


# ==============================================================================
# 5. Non-Negotiable Privacy & Zero-Contract-Storage Invariant Tests
# ==============================================================================


@pytest.mark.django_db
class TestZeroContractStoragePipelineInvariant:
    """Non-Negotiable Project Invariant: The corpus pipeline processes reviewed standards ONLY."""

    def test_zero_contract_storage_pipeline_isolation(self) -> None:
        """Assert pipeline data structures and database tables handle only reviewed standards.

        Verifies:
        1. No user contract identifiers, artist uploads, or user sessions exist in the pipeline.
        2. Chunks are strictly coupled to CorpusVersion and ReferenceSource.
        """
        sources, clauses = get_default_synthetic_standards()
        publisher = CorpusPublisher()
        res = publisher.publish_version("v1.0.0-privacy", sources, clauses, activate=True)

        assert res.published is True
        snapshot = load_corpus_snapshot()
        assert snapshot is not None

        # Confirm all metadata corresponds to public reference standards
        for chunk in snapshot.chunks:
            assert chunk.source_license in [
                "CC BY 4.0",
                "Kenya Copyright Act (Cap. 130)",
            ]
            assert "user" not in chunk.metadata
            assert "session" not in chunk.metadata
            assert "contract_id" not in chunk.metadata
