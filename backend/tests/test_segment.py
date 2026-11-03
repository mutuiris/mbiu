"""Comprehensive unit and property tests for contract clause segmentation.

Verifies:
1. Hypothesis property tests:
   - Offsets slice back exactly: full_text[clause.start_offset:clause.end_offset] == clause.text
   - Clauses never overlap in their character offset ranges
   - Clauses spanning a page break keep all touched page numbers
2. Synthetic contract test scenarios:
   - Synthetic Recording Contract (preamble, recitals, nested 1.1(a)(i), schedules, defined terms)
   - Synthetic Gig Contract (unnumbered headings, inline defined terms, layout cues)
   - Synthetic Producer Contract (Roman numerals, Annexes, fee structures)
3. Edge cases and zero-storage verification:
   - Empty/whitespace documents
   - Documents with skipped/scanned pages
   - Zero temporary file creation
"""

import os
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from mbiu.documents.extract import ExtractedDocument, PageText, extract_text_in_process
from mbiu.documents.segment import segment_document, segment_text
from tests.pdf_factories import create_synthetic_text_pdf

# -----------------------------------------------------------------------------
# Synthetic Contract Fixtures
# -----------------------------------------------------------------------------

SYNTHETIC_RECORDING_CONTRACT = """RECORDING AGREEMENT

This Agreement is made on 1st November 2026 between SoundWave Records Limited (the "Company")
and Jane Wanjiku professionally known as "Wanjiku" (the "Artist").

RECITALS:
(A) The Company operates an independent record label in Kenya.
(B) The Artist is a recording musical artist wishing to produce and release sound recordings.

NOW IT IS HEREBY AGREED as follows:

1. DEFINITIONS AND INTERPRETATION
1.1 In this Agreement, unless the context otherwise requires:
"Net Receipts" means all gross monies actually received by the Company from the exploitation
of the Masters less standard distribution commissions and statutory withholding taxes;
"Advance": the sum of KES 150,000 payable upon execution of this Agreement;
"Territory" shall mean the Republic of Kenya and the rest of the world;
"Masters" refers to the master sound recordings delivered under Clause 2.

2. RECORDING COMMITMENT
2.1 The Artist shall record and deliver to the Company six (6) master recordings.
2.2 All recordings shall be technically and commercially satisfactory to the Company.

3. ROYALTIES AND ACCOUNTINGS
3.1 Royalties. The Company shall pay to the Artist:
(a) 18% of Net Receipts derived from physical album sales;
(b) 22% of Net Receipts derived from digital streaming:
(i) for on-demand audio streams;
(ii) for video synchronization streams.
3.2 Accountings shall be rendered semi-annually within sixty (60) days
following 30 June and 31 December.

4. DURATION AND TERMINATION
4.1 The initial term of this Agreement shall be two (2) years from the Effective Date.
4.2 Either party may terminate upon thirty (30) days written notice for material breach.

SCHEDULE 1: RECORDING BUDGET
1. Studio Allocation
1.1 The studio recording budget ceiling is KES 300,000 per album.
1.2 Mastering costs shall be paid directly by the Company.

SCHEDULE 2: DELIVERY REQUIREMENTS
1. Technical Specifications
1.1 All masters must be delivered in 24-bit 96kHz WAV format.

IN WITNESS WHEREOF the parties have executed this Agreement as of the date first above written.
Signed by SoundWave Records Limited: ___________________
Signed by Jane Wanjiku: ___________________
"""

SYNTHETIC_GIG_CONTRACT = """LIVE PERFORMANCE AGREEMENT

This Live Gig Agreement is dated 15 December 2026 between Nairobi Live Venues (the "Promoter")
and John Ochieng (the "Artist").

ENGAGEMENT AND VENUE
The Artist is engaged to perform a 90-minute live musical set at The Junction Courtyard
on 31 December 2026 commencing at 21:00 EAT.

COMPENSATION AND EXPENSES
The Promoter shall pay the Artist a guaranteed fee of KES 80,000 payable as follows:
a 50% deposit upon signing and the remaining 50% immediately upon conclusion of the performance.
The Promoter shall provide local hospitality and KES 10,000 per diem.

SOUND AND TECHNICAL RIDERS
The Promoter warrants that professional sound reinforcement, monitors, and lighting
meeting the Artist's technical rider will be fully operational at soundcheck.

CANCELLATION AND FORCE MAJEURE
If the performance is cancelled due to adverse weather or force majeure, the Artist
shall retain the 50% deposit and neither party shall have further liability.

SIGNATURES
Promoter: ___________________
Artist: ___________________
"""

SYNTHETIC_PRODUCER_CONTRACT = """MUSIC PRODUCTION AGREEMENT

This Producer Agreement is entered into between Nairobi Groove Productions (the "Label")
and David Mwangi (the "Producer").

1. PRODUCTION SERVICES
1.1 The Producer agrees to produce and mix three (3) musical tracks (the "Tracks").

2. PRODUCER ROYALTIES
2.1 Production Royalty. The Label shall pay the Producer a royalty of 3% of Retail Sales.
2.2 The royalty shall be calculated as follows:
(a) on all physical reproduction sales;
(b) on all streaming revenue:
(i) interactive streaming services;
(ii) non-interactive internet radio.

3. CREDITS
3.1 The Producer shall receive credit on all releases as "Produced by David Mwangi".

ANNEX A: STEM DELIVERABLES
1. Delivery Items
1.1 Producer shall deliver mixed stems, pro tools session files, and instrumental tracks.

IN WITNESS WHEREOF the parties have signed below.
"""


# -----------------------------------------------------------------------------
# Hypothesis Property Tests
# -----------------------------------------------------------------------------

# Strategy for building realistic contract clauses
_CLAUSE_NUMBER_STRATEGY = st.sampled_from(
    [
        "1.",
        "2.",
        "3.",
        "1.1",
        "1.2",
        "2.1.1",
        "(a)",
        "(b)",
        "(c)",
        "(i)",
        "(ii)",
        "Clause 1.",
        "Section 2.1",
        "SCHEDULE 1",
        "ANNEX A",
    ]
)

_TEXT_CHUNK_STRATEGY = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
        whitelist_characters=".,;-:",
    ),
    min_size=5,
    max_size=120,
)


@st.composite
def synthetic_document_strategy(draw: st.DrawFn) -> ExtractedDocument:
    """Hypothesis composite strategy to generate synthetic multi-page ExtractedDocuments."""
    num_clauses = draw(st.integers(min_value=2, max_value=8))
    clause_blocks: list[str] = []

    for _ in range(num_clauses):
        marker = draw(_CLAUSE_NUMBER_STRATEGY)
        body = draw(_TEXT_CHUNK_STRATEGY).strip()
        clause_blocks.append(f"{marker} {body}")

    full_text = "\n\n".join(clause_blocks)

    # Randomly distribute full_text across 1 to 4 pages
    num_pages = draw(st.integers(min_value=1, max_value=4))
    text_len = len(full_text)

    pages: list[PageText] = []
    if num_pages == 1 or text_len == 0:
        pages.append(
            PageText(
                page_number=1,
                text=full_text,
                start_offset=0,
                end_offset=text_len,
                has_text=bool(full_text.strip()),
            )
        )
    else:
        # Choose split points
        split_points = sorted(
            draw(
                st.lists(
                    st.integers(min_value=1, max_value=max(1, text_len - 1)),
                    min_size=num_pages - 1,
                    max_size=num_pages - 1,
                    unique=True,
                )
            )
        )
        boundaries = [0] + split_points + [text_len]
        for idx in range(num_pages):
            p_start = boundaries[idx]
            p_end = boundaries[idx + 1]
            p_text = full_text[p_start:p_end]
            pages.append(
                PageText(
                    page_number=idx + 1,
                    text=p_text,
                    start_offset=p_start,
                    end_offset=p_end,
                    has_text=bool(p_text.strip()),
                )
            )

    return ExtractedDocument(
        pages=pages,
        full_text=full_text,
        total_pages=len(pages),
        skipped_pages=[],
    )


class TestClauseSplitterProperties:
    """Hypothesis property tests asserting Project Invariants."""

    @given(doc=synthetic_document_strategy())
    @settings(max_examples=50)
    def test_offsets_slice_back_exactly(self, doc: ExtractedDocument) -> None:
        """Property: for every clause, full_text[start_offset:end_offset] == clause.text."""
        segmented = segment_document(doc)
        for clause in segmented.clauses:
            actual_slice = doc.full_text[clause.start_offset : clause.end_offset]
            assert actual_slice == clause.text, (
                f"Offset mismatch for clause '{clause.clause_id}': "
                f"slice '{actual_slice}' != text '{clause.text}'"
            )

    @given(doc=synthetic_document_strategy())
    @settings(max_examples=50)
    def test_clauses_never_overlap(self, doc: ExtractedDocument) -> None:
        """Property: clauses never overlap in their character offset ranges."""
        segmented = segment_document(doc)
        clauses = segmented.clauses
        for i in range(len(clauses) - 1):
            current_clause = clauses[i]
            next_clause = clauses[i + 1]
            assert current_clause.end_offset <= next_clause.start_offset, (
                f"Overlap detected: clause {current_clause.clause_id} "
                f"[{current_clause.start_offset}:{current_clause.end_offset}] overlaps with "
                f"clause {next_clause.clause_id} "
                f"[{next_clause.start_offset}:{next_clause.end_offset}]"
            )

    @given(doc=synthetic_document_strategy())
    @settings(max_examples=50)
    def test_clauses_spanning_page_breaks_keep_all_pages(self, doc: ExtractedDocument) -> None:
        """Property: clauses spanning page breaks keep all relevant page numbers."""
        segmented = segment_document(doc)
        for clause in segmented.clauses:
            # Check which pages overlap with [clause.start_offset, clause.end_offset)
            expected_pages: list[int] = []
            for p in doc.pages:
                if not p.has_text:
                    continue
                if max(clause.start_offset, p.start_offset) < min(clause.end_offset, p.end_offset):
                    expected_pages.append(p.page_number)

            if expected_pages:
                assert clause.pages == expected_pages, (
                    f"Clause {clause.clause_id} pages {clause.pages} != expected {expected_pages}"
                )


# -----------------------------------------------------------------------------
# Unit Tests with Synthetic Contracts
# -----------------------------------------------------------------------------


class TestSyntheticRecordingContract:
    """Unit tests for realistic recording contract with nested clauses and schedules."""

    def test_segment_synthetic_recording_contract(self) -> None:
        """Test complete segmentation of recording contract."""
        segmented = segment_text(SYNTHETIC_RECORDING_CONTRACT, page_count=3)

        assert segmented.total_clauses > 10
        clause_ids = [c.clause_id for c in segmented.clauses]

        # Verify preamble
        preamble = segmented.get_clause("preamble")
        assert preamble is not None
        assert "RECORDING AGREEMENT" in preamble.text
        assert preamble.section == "Preamble"

        # Verify recitals
        assert "recital_A" in clause_ids
        assert "recital_B" in clause_ids

        # Verify main numbered clauses
        assert "1" in clause_ids or "1.1" in clause_ids
        assert "2" in clause_ids or "2.1" in clause_ids
        assert "3" in clause_ids or "3.1" in clause_ids

        # Verify nested numbering
        assert "3.1(a)" in clause_ids
        assert "3.1(b)" in clause_ids
        assert "3.1(b)(i)" in clause_ids
        assert "3.1(b)(ii)" in clause_ids

        # Verify schedules preserved as distinct sections
        schedule_1_clauses = [c for c in segmented.clauses if "Schedule 1" in c.section]
        assert len(schedule_1_clauses) >= 2
        schedule_2_clauses = [c for c in segmented.clauses if "Schedule 2" in c.section]
        assert len(schedule_2_clauses) >= 2

        # Verify defined terms extracted
        assert "Net Receipts" in segmented.defined_terms
        assert "Advance" in segmented.defined_terms
        assert "Territory" in segmented.defined_terms
        assert "Masters" in segmented.defined_terms
        assert "Artist" in segmented.defined_terms
        assert "Company" in segmented.defined_terms

        # Verify get_definition helper with case and quotes tolerance
        net_receipts_def = segmented.get_definition("Net Receipts")
        assert net_receipts_def is not None
        assert "gross monies" in net_receipts_def.lower()

        quoted_lookup = segmented.get_definition('"Net Receipts"')
        assert quoted_lookup == net_receipts_def

        lower_lookup = segmented.get_definition("net receipts")
        assert lower_lookup == net_receipts_def

        # Verify slice-back for all clauses
        for c in segmented.clauses:
            assert SYNTHETIC_RECORDING_CONTRACT[c.start_offset : c.end_offset] == c.text
            assert c.text == c.text.strip()


class TestSyntheticGigContract:
    """Unit tests for gig contract with unnumbered headings and layout structure."""

    def test_segment_synthetic_gig_contract(self) -> None:
        """Test segmentation of unnumbered gig agreement."""
        segmented = segment_text(SYNTHETIC_GIG_CONTRACT, page_count=2)

        assert segmented.total_clauses >= 4
        clause_ids = [c.clause_id for c in segmented.clauses]

        # Check heading-based clause identification
        assert any("engagement" in cid for cid in clause_ids)
        assert any("compensation" in cid for cid in clause_ids)
        assert any("sound" in cid for cid in clause_ids)
        assert any("cancellation" in cid for cid in clause_ids)

        # Check inline defined terms
        assert "Artist" in segmented.defined_terms
        assert "Promoter" in segmented.defined_terms

        # Verify non-overlapping offsets
        for i in range(len(segmented.clauses) - 1):
            assert segmented.clauses[i].end_offset <= segmented.clauses[i + 1].start_offset


class TestSyntheticProducerContract:
    """Unit tests for producer agreement with Annex and Roman numeral subclauses."""

    def test_segment_synthetic_producer_contract(self) -> None:
        """Test segmentation of producer agreement."""
        segmented = segment_text(SYNTHETIC_PRODUCER_CONTRACT, page_count=2)

        clause_ids = [c.clause_id for c in segmented.clauses]
        assert "1" in clause_ids or "1.1" in clause_ids
        assert "2.1" in clause_ids
        assert "2.2(a)" in clause_ids
        assert "2.2(b)" in clause_ids
        assert "2.2(b)(i)" in clause_ids
        assert "2.2(b)(ii)" in clause_ids

        # Verify Annex section
        annex_clauses = [c for c in segmented.clauses if "Annex" in c.section]
        assert len(annex_clauses) >= 1

        # Check title extraction
        royalty_clause = segmented.get_clause("2.1")
        if royalty_clause:
            assert royalty_clause.title == "Production Royalty"


# -----------------------------------------------------------------------------
# Edge Cases & Project Invariants
# -----------------------------------------------------------------------------


class TestSegmenterEdgeCases:
    """Test edge conditions, multi-page breaks, and non-negotiable invariants."""

    def test_empty_string_returns_empty_result(self) -> None:
        """Empty string returns empty SegmentedDocument without error."""
        res = segment_text("")
        assert res.total_clauses == 0
        assert res.clauses == []
        assert res.defined_terms == {}
        assert res.sections == []

    def test_whitespace_only_returns_empty_result(self) -> None:
        """Whitespace-only string returns empty result."""
        res = segment_text("   \n\n\t   \n")
        assert res.total_clauses == 0
        assert res.clauses == []

    def test_single_clause_document(self) -> None:
        """Single paragraph contract produces a single valid clause."""
        raw = "1. Grant of Rights. The Artist grants exclusive publishing rights to the Company."
        res = segment_text(raw)
        assert res.total_clauses == 1
        clause = res.clauses[0]
        assert clause.clause_id == "1"
        assert clause.title == "Grant of Rights"
        assert clause.text == raw
        assert raw[clause.start_offset : clause.end_offset] == clause.text

    def test_clause_spanning_three_pages(self) -> None:
        """A single long clause spanning three pages retains [1, 2, 3] page numbers."""
        p1 = "1. Extensive Clause\nThis is the beginning of the clause on page 1.\n"
        p2 = "This is the continuation of the clause on page 2.\n"
        p3 = "This is the conclusion of the clause on page 3.\n"
        full = p1 + p2 + p3

        doc = ExtractedDocument(
            pages=[
                PageText(
                    page_number=1,
                    text=p1,
                    start_offset=0,
                    end_offset=len(p1),
                    has_text=True,
                ),
                PageText(
                    page_number=2,
                    text=p2,
                    start_offset=len(p1),
                    end_offset=len(p1) + len(p2),
                    has_text=True,
                ),
                PageText(
                    page_number=3,
                    text=p3,
                    start_offset=len(p1) + len(p2),
                    end_offset=len(full),
                    has_text=True,
                ),
            ],
            full_text=full,
            total_pages=3,
            skipped_pages=[],
        )

        segmented = segment_document(doc)
        assert segmented.total_clauses == 1
        clause = segmented.clauses[0]
        assert clause.pages == [1, 2, 3]
        assert full[clause.start_offset : clause.end_offset] == clause.text

    def test_document_with_skipped_scanned_page(self) -> None:
        """Middle page without text is not included in touched clause pages."""
        p1 = "1. First Term\nText on page one.\n"
        p2 = ""  # Scanned or blank page
        p3 = "2. Second Term\nText on page three.\n"
        full = p1 + p2 + p3

        doc = ExtractedDocument(
            pages=[
                PageText(
                    page_number=1,
                    text=p1,
                    start_offset=0,
                    end_offset=len(p1),
                    has_text=True,
                ),
                PageText(
                    page_number=2,
                    text=p2,
                    start_offset=len(p1),
                    end_offset=len(p1),
                    has_text=False,
                ),
                PageText(
                    page_number=3,
                    text=p3,
                    start_offset=len(p1),
                    end_offset=len(full),
                    has_text=True,
                ),
            ],
            full_text=full,
            total_pages=3,
            skipped_pages=[2],
        )

        segmented = segment_document(doc)
        assert segmented.total_clauses == 2
        assert segmented.clauses[0].pages == [1]
        assert segmented.clauses[1].pages == [3]

    def test_end_to_end_from_synthetic_pdf(self) -> None:
        """Extract text from synthetic PDF in memory and segment clauses end-to-end."""
        pdf_bytes = create_synthetic_text_pdf(
            [
                "RECORDING CONTRACT\n\n1. Grant of Rights\nThe Artist grants all rights.",
                (
                    "2. Royalties\nThe Company pays 15% Net Receipts.\n\n"
                    "SCHEDULE 1\nBudget: KES 100,000"
                ),
            ]
        )
        extracted = extract_text_in_process(pdf_bytes)
        segmented = segment_document(extracted)

        assert segmented.total_clauses >= 2
        for c in segmented.clauses:
            assert extracted.full_text[c.start_offset : c.end_offset] == c.text

    def test_zero_contract_storage_in_temp_directory(self) -> None:
        """Enforces zero contract storage: segmentation creates 0 files in temp storage."""
        temp_dir = tempfile.gettempdir()
        initial_files = set(os.listdir(temp_dir))

        # Perform complex segmentation in memory
        res = segment_text(SYNTHETIC_RECORDING_CONTRACT, page_count=4)
        assert res.total_clauses > 0

        current_files = set(os.listdir(temp_dir))
        new_files = current_files - initial_files

        # Assert no temp files were created
        assert not new_files, f"Leaked temporary files during segmentation: {new_files}"
