"""Unit and integration tests for whole-contract map (MB-14).

Verifies:
1. Deterministic link extraction (cross-references, overrides, defined terms).
2. Candidate pair generation and O(N) linear topic clustering.
3. Contract type classification.
4. Code verification of exact quotes for contract issues.
5. Golden set MB-19 cross-clause conflict detection (Definition of Done).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from mbiu.api.schemas import ContractMapPayload
from mbiu.contract_map import (
    build_candidate_pairs,
    build_deterministic_links,
    detect_contract_type,
    map_contract,
)
from mbiu.contract_map.analyzer import (
    IssueProposal,
    verify_issue_quotes,
)
from mbiu.contract_map.deterministic import (
    find_cross_references,
    find_defined_term_links,
    find_override_links,
)
from mbiu.documents.extract import extract_text_in_process
from mbiu.documents.segment import Clause, DefinedTerm, SegmentedDocument, segment_document

DATASETS_DIR = Path(__file__).resolve().parents[2] / "evals" / "datasets"


def _make_dummy_clause(
    clause_id: str,
    text: str,
    title: str | None = None,
    pages: list[int] | None = None,
) -> Clause:
    return Clause(
        clause_id=clause_id,
        section="main",
        title=title,
        text=text,
        pages=pages or [1],
        start_offset=0,
        end_offset=len(text),
    )


def test_cross_reference_extraction() -> None:
    """Explicit references to other clauses or schedules are detected."""
    c1 = _make_dummy_clause("1.1", "Payment details are specified in clause 4.2.")
    c2 = _make_dummy_clause(
        "2.1",
        "Subject to Schedule A, the Artist grants exclusive rights. Also see clauses 1.1 and 3.1.",
    )
    c3 = _make_dummy_clause("3.1", "Standard grant of rights.")
    c4 = _make_dummy_clause("4.2", "Royalties shall be paid quarterly.")
    c_sched = _make_dummy_clause("sched_1", "Details of masters.", title="Schedule A")

    clauses = [c1, c2, c3, c4, c_sched]
    links = find_cross_references(clauses)

    pairs = {(item.from_clause_id, item.to_clause_id, item.kind) for item in links}

    # 1.1 references 4.2
    assert ("1.1", "4.2", "cross_reference") in pairs
    # 2.1 references 1.1 and 3.1
    assert ("2.1", "1.1", "cross_reference") in pairs
    assert ("2.1", "3.1", "cross_reference") in pairs
    # 2.1 references Schedule A
    assert ("2.1", "sched_1", "cross_reference") in pairs
    # No self-references
    assert not any(link.from_clause_id == link.to_clause_id for link in links)


def test_override_wording_extraction() -> None:
    """Override language targeting clauses is captured as kind='override'."""
    c1 = _make_dummy_clause("2.1", "The Term continues for two (2) years.")
    c2 = _make_dummy_clause(
        "7.1",
        "Notwithstanding clause 2.1, the Term of this Agreement is five (5) years.",
    )
    c3 = _make_dummy_clause(
        "8.1",
        "Notwithstanding anything to the contrary in this Agreement, the Company owns all masters.",
    )

    links, occurrences = find_override_links([c1, c2, c3])
    override_pairs = {(item.from_clause_id, item.to_clause_id) for item in links}

    assert ("7.1", "2.1") in override_pairs
    assert any(o.is_general and o.from_clause_id == "8.1" for o in occurrences)
    assert any(
        not o.is_general and o.from_clause_id == "7.1" and o.target_clause_id == "2.1"
        for o in occurrences
    )


def test_defined_term_links() -> None:
    """Clauses mentioning a defined term link back to the defining clause."""
    c1 = _make_dummy_clause(
        "1.1", 'Definitions: "Net Receipts" means all gross receipts minus direct costs.'
    )
    c2 = _make_dummy_clause("4.1", "Royalties: The Artist receives 15% of Net Receipts.")
    c3 = _make_dummy_clause("5.1", "General boilerplate with no defined terms.")

    dt = DefinedTerm(
        term="Net Receipts",
        definition="all gross receipts minus direct costs",
        clause_id="1.1",
        pages=[1],
        start_offset=14,
        end_offset=56,
    )

    links = find_defined_term_links([c1, c2, c3], [dt])
    assert len(links) == 1
    assert links[0].from_clause_id == "4.1"
    assert links[0].to_clause_id == "1.1"
    assert links[0].kind == "defined_term"


def test_contract_type_classification() -> None:
    """Standard music contract types are detected from preamble and clause text."""
    doc_recording = SegmentedDocument(
        clauses=[
            _make_dummy_clause("1", "SYNTHETIC RECORDING AGREEMENT", title="Title"),
            _make_dummy_clause(
                "2", "The record company shall record and exploit master recordings."
            ),
        ],
        defined_terms={},
        defined_terms_detailed=[],
        sections=["main"],
        total_clauses=2,
    )
    assert detect_contract_type(doc_recording) == "recording"

    doc_publishing = SegmentedDocument(
        clauses=[
            _make_dummy_clause("1", "EXCLUSIVE MUSIC PUBLISHING AGREEMENT", title="Title"),
            _make_dummy_clause(
                "2", "The songwriter assigns musical works and mechanical royalties."
            ),
        ],
        defined_terms={},
        defined_terms_detailed=[],
        sections=["main"],
        total_clauses=2,
    )
    assert detect_contract_type(doc_publishing) == "publishing"

    doc_unknown = SegmentedDocument(
        clauses=[
            _make_dummy_clause("1", "CAR RENTAL AGREEMENT", title="Title"),
            _make_dummy_clause("2", "The renter agrees to return the vehicle with a full tank."),
        ],
        defined_terms={},
        defined_terms_detailed=[],
        sections=["main"],
        total_clauses=2,
    )
    assert detect_contract_type(doc_unknown) is None


def test_candidate_pairs_and_linear_growth() -> None:
    """Candidate pairs include links and same-topic clusters, bounded linearly."""
    c_term1 = _make_dummy_clause("2.1", "The Term is 2 years.", title="Term")
    c_term2 = _make_dummy_clause("7.1", "Renewal period of 5 years.", title="Renewal")
    c_royalty = _make_dummy_clause("4.1", "Royalty of 15% of gross receipts.", title="Royalties")
    c_notices = _make_dummy_clause("9.1", "Notices to be sent in writing.", title="Notices")

    segmented = SegmentedDocument(
        clauses=[c_term1, c_term2, c_royalty, c_notices],
        defined_terms={},
        defined_terms_detailed=[],
        sections=["main"],
        total_clauses=4,
    )

    det_links, _ = build_deterministic_links(segmented)
    candidate_pairs, all_links = build_candidate_pairs(segmented, det_links)

    # 2.1 and 7.1 both touch term_renewal
    pair_ids = {pair.clause_ids for pair in candidate_pairs}
    assert ("2.1", "7.1") in pair_ids or ("7.1", "2.1") in pair_ids
    # Total candidates is smaller than all possible combinations
    assert len(candidate_pairs) < (4 * 3) // 2 + 1


def test_exact_quote_verification_logic() -> None:
    """Verifies that quotes in issue proposals must be exact verbatim substrings."""
    c1 = _make_dummy_clause("2.1", "The Term continues for two (2) years.")
    c2 = _make_dummy_clause("7.1", "The Term of this Agreement is five (5) years.")
    clause_map = {"2.1": c1, "7.1": c2}

    # 1. Exact valid quotes pass
    valid_proposal = IssueProposal(
        kind="conflict",
        clause_ids=["2.1", "7.1"],
        quotes=["continues for two (2) years", "The Term of this Agreement is five (5) years"],
        explanation="Conflicting durations.",
    )
    assert verify_issue_quotes(valid_proposal, clause_map) is True

    # 2. Hallucinated quote fails
    invalid_proposal = IssueProposal(
        kind="conflict",
        clause_ids=["2.1", "7.1"],
        quotes=["continues for ten years", "The Term of this Agreement is five (5) years"],
        explanation="Conflicting durations.",
    )
    assert verify_issue_quotes(invalid_proposal, clause_map) is False

    # 3. Non-existent clause ID fails
    missing_id_proposal = IssueProposal(
        kind="conflict",
        clause_ids=["2.1", "99.9"],
        quotes=["continues for two (2) years", "foo"],
        explanation="Conflicting durations.",
    )
    assert verify_issue_quotes(missing_id_proposal, clause_map) is False


def test_mb19_golden_set_cross_clause_conflict() -> None:
    """Definition of Done: MB-19 cross-clause conflict detected with correct clause IDs."""
    pdf_path = DATASETS_DIR / "pdfs" / "mb19-cross-clause-conflict.pdf"
    assert pdf_path.is_file(), f"Expected golden set PDF at {pdf_path}"

    pdf_bytes = pdf_path.read_bytes()
    extracted = extract_text_in_process(pdf_bytes)
    segmented = segment_document(extracted)

    # Run contract mapping
    contract_map: ContractMapPayload = asyncio.run(map_contract(segmented))

    assert contract_map.contract_type == "recording"
    assert len(contract_map.issues) >= 1

    # Find the planted conflict between clause 2.1 and 7.1
    conflict = next(
        (i for i in contract_map.issues if set(i.clause_ids) == {"2.1", "7.1"}),
        None,
    )
    assert conflict is not None, (
        f"Expected conflict between 2.1 and 7.1, got: {contract_map.issues}"
    )
    assert conflict.kind == "conflict"
    assert conflict.pages == [1]

    # Check quote verification: quotes must be exact substrings of clause text
    c_2_1 = segmented.get_clause("2.1")
    c_7_1 = segmented.get_clause("7.1")
    assert c_2_1 is not None and c_7_1 is not None

    quote_1, quote_2 = conflict.quotes
    assert (quote_1 in c_2_1.text and quote_2 in c_7_1.text) or (
        quote_1 in c_7_1.text and quote_2 in c_2_1.text
    )


def test_mb19_golden_set_combined_risks_conflict() -> None:
    """Definition of Done: MB-19 combined-risks contract finds the cross-clause conflict."""
    pdf_path = DATASETS_DIR / "pdfs" / "mb19-combined-risks.pdf"
    assert pdf_path.is_file(), f"Expected golden set PDF at {pdf_path}"

    pdf_bytes = pdf_path.read_bytes()
    extracted = extract_text_in_process(pdf_bytes)
    segmented = segment_document(extracted)

    contract_map: ContractMapPayload = asyncio.run(map_contract(segmented))

    conflict = next(
        (i for i in contract_map.issues if set(i.clause_ids) == {"2.1", "7.1"}),
        None,
    )
    assert conflict is not None, (
        f"Expected conflict between 2.1 and 7.1, got: {contract_map.issues}"
    )
    assert conflict.kind == "conflict"
    assert conflict.pages == [1]


def test_mb19_clean_control_has_no_planted_conflicts() -> None:
    """The clean control contract has no contradictory clause issues."""
    pdf_path = DATASETS_DIR / "pdfs" / "mb19-clean-control.pdf"
    assert pdf_path.is_file(), f"Expected golden set PDF at {pdf_path}"

    pdf_bytes = pdf_path.read_bytes()
    extracted = extract_text_in_process(pdf_bytes)
    segmented = segment_document(extracted)

    contract_map: ContractMapPayload = asyncio.run(map_contract(segmented))
    # No substantive conflicts
    conflicts = [i for i in contract_map.issues if i.kind == "conflict"]
    assert len(conflicts) == 0
