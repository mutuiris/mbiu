"""Clause segmentation and defined-terms extraction for contracts.

Splits extracted document text into structured clauses using numbering
(e.g., 1, 1.1, (a), (i)), headings, and layout cues.
Maintains exact character offsets, section separation (main body vs schedules/annexes),
multi-page provenance, and defined terms mapping for whole-contract analysis.

Enforces zero-storage invariants: operates purely in memory with zero persistence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from mbiu.documents.extract import ExtractedDocument, PageText


@dataclass(frozen=True)
class Clause:
    """Extracted clause with exact offsets, page numbers, and structural metadata.

    Attributes:
        clause_id: Unique hierarchical identifier (e.g. "1", "1.1", "1.1(a)", "schedule_1_1").
        section: Section name (e.g. "main", "Schedule 1", "Annex A", "Recitals", "Signatures").
        title: Title or heading of the clause, or None if untitled.
        text: Exact substring of the document's full text.
        pages: List of 1-indexed page numbers spanned by the clause.
        start_offset: Character start offset within the document's full text (inclusive).
        end_offset: Character end offset within the document's full text (exclusive).
    """

    clause_id: str
    section: str
    title: str | None
    text: str
    pages: list[int]
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class DefinedTerm:
    """Defined term extracted from contract text.

    Attributes:
        term: Normalized defined term string (e.g. "Net Receipts").
        definition: Text of the definition.
        clause_id: ID of the clause where the term is defined.
        pages: List of 1-indexed page numbers spanned by the definition.
        start_offset: Character start offset within full text.
        end_offset: Character end offset within full text.
    """

    term: str
    definition: str
    clause_id: str
    pages: list[int]
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class SegmentedDocument:
    """Complete segmented representation of a contract.

    Attributes:
        clauses: List of clauses in document order.
        defined_terms: Dictionary mapping defined term strings to their definitions.
        defined_terms_detailed: Detailed DefinedTerm records with clause and offset provenance.
        sections: Distinct section names in order of appearance.
        total_clauses: Total count of clauses.
    """

    clauses: list[Clause]
    defined_terms: dict[str, str]
    defined_terms_detailed: list[DefinedTerm]
    sections: list[str]
    total_clauses: int

    def get_definition(self, term: str) -> str | None:
        """Look up a definition by term name, ignoring case and surrounding quotation marks.

        Args:
            term: The term name to query.

        Returns:
            The definition string if found, otherwise None.
        """
        cleaned = term.strip("\"'“”‘’")
        if cleaned in self.defined_terms:
            return self.defined_terms[cleaned]
        cleaned_lower = cleaned.lower()
        for k, v in self.defined_terms.items():
            if k.lower() == cleaned_lower:
                return v
        return None

    def get_clause(self, clause_id: str) -> Clause | None:
        """Look up a clause by its unique clause_id.

        Args:
            clause_id: The clause identifier.

        Returns:
            The matching Clause if found, otherwise None.
        """
        for c in self.clauses:
            if c.clause_id == clause_id:
                return c
        return None


# Regular expressions for structural boundaries
_SECTION_SCHEDULE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(SCHEDULE|ANNEX|ANNEXURE|EXHIBIT|APPENDIX)\s+([0-9A-Za-z]+)(?:\s*[:\-–—]\s*(.*))?$",
    re.IGNORECASE,
)

_SECTION_RECITALS_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(RECITALS|BACKGROUND|PREAMBLE)\s*[:\-–—]?\s*$",
    re.IGNORECASE,
)

_SECTION_EXECUTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(IN WITNESS WHEREOF|EXECUTION|SIGNATURES|SIGNED BY)\b.*$",
    re.IGNORECASE,
)

_DECIMAL_NUMBER_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(\d+(?:\.\d+)+)\b\.?\s*(.*)$",
)

_INTEGER_NUMBER_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(\d+)\.\s+(.*)$",
)

_EXPLICIT_CLAUSE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:Clause|Section|Article)\s+([0-9IVXLCDM]+(?:\.[0-9]+)*)\b\.?\s*(.*)$",
    re.IGNORECASE,
)

_PAREN_SUBCLAUSE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*\(([a-z0-9]+)\)\s+(.*)$",
)

_ROMAN_SUBCLAUSE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*\((i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,3})\)\s+(.*)$",
    re.IGNORECASE,
)

_ROMAN_DOT_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,3})\.\s+(.*)$",
    re.IGNORECASE,
)

_LETTER_DOT_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*([a-z])\.\s+(.*)$",
)

_RECITAL_LETTER_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*\(([A-Z])\)\s+(.*)$",
)

_ALL_CAPS_HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*([A-Z][A-Z0-9\s\-_/&,]{2,70})\s*$",
)

_STOP_HEADINGS: Final[set[str]] = {
    "AND",
    "OR",
    "BETWEEN",
    "WHEREAS",
    "NOW THEREFORE",
    "WITNESSETH",
    "PAGE",
    "DATED",
    "BY AND BETWEEN",
    "NOW IT IS HEREBY AGREED",
}

_INLINE_TITLE_RE: Final[re.Pattern[str]] = re.compile(
    r"^([A-Z][A-Za-z0-9\s\-_/&]{1,60})\s*(?:[:\-–—]|\.\s+)\s*(.*)$",
)

_TITLE_VERBS: Final[set[str]] = {
    "is",
    "are",
    "shall",
    "will",
    "agrees",
    "agreed",
    "warrants",
    "represents",
    "undertakes",
    "hereby",
    "may",
}


def _clean_slug(name: str) -> str:
    """Convert a section title or name into a clean alphanumeric slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip()).strip("_").lower()
    return slug or "section"


def _extract_title_from_rest(rest: str) -> tuple[str | None, str]:
    """Attempt to extract an inline heading or title from remainder of a numbered line."""
    rest_clean = rest.strip()
    if not rest_clean:
        return None, ""

    # Check for inline title like "Royalties. The Company shall pay..."
    inline_match = _INLINE_TITLE_RE.match(rest_clean)
    if inline_match:
        candidate_title = inline_match.group(1).strip()
        words = candidate_title.lower().split()
        if not any(v in words for v in _TITLE_VERBS) and len(words) <= 7:
            return candidate_title, inline_match.group(2).strip()

    # Check if the entire rest is a short standalone heading (e.g. "ROYALTIES" or "Grant of Rights")
    if len(rest_clean) <= 60 and not rest_clean.endswith((".", ";", ":", ",")):
        words = rest_clean.lower().split()
        if not any(v in words for v in _TITLE_VERBS) and len(words) <= 7:
            return rest_clean, ""

    return None, rest_clean


@dataclass
class _LineInfo:
    """Metadata for an identified line."""

    start_offset: int
    end_offset: int
    text: str
    is_boundary: bool
    is_section_boundary: bool
    new_section: str | None
    number: str | None
    number_type: str | None  # "decimal", "integer", "paren", "letter_dot", "roman", "recital"
    title: str | None


def _classify_line(line_start: int, line_end: int, line_text: str) -> _LineInfo:
    """Classify a line for section and clause boundaries."""
    stripped = line_text.strip()
    if not stripped:
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=False,
            is_section_boundary=False,
            new_section=None,
            number=None,
            number_type=None,
            title=None,
        )

    # 1. Schedule / Annex / Exhibit / Appendix
    sched_match = _SECTION_SCHEDULE_RE.match(line_text)
    if sched_match:
        kind = sched_match.group(1).title()
        ident = sched_match.group(2).upper()
        raw_title = sched_match.group(3)
        title = raw_title.strip() if raw_title else None
        section_name = f"{kind} {ident}"
        if title:
            section_name = f"{section_name}: {title}"
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=True,
            new_section=section_name,
            number=None,
            number_type=None,
            title=title or f"{kind} {ident}",
        )

    # 2. Recitals / Background / Preamble
    recitals_match = _SECTION_RECITALS_RE.match(line_text)
    if recitals_match:
        section_name = recitals_match.group(1).title()
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=True,
            new_section=section_name,
            number=None,
            number_type=None,
            title=section_name,
        )

    # 3. Execution / Signatures
    exec_match = _SECTION_EXECUTION_RE.match(line_text)
    if exec_match:
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=True,
            new_section="Signatures",
            number=None,
            number_type=None,
            title="Signatures",
        )

    # 4. Decimal number (e.g. 1.1, 1.2.3)
    dec_match = _DECIMAL_NUMBER_RE.match(line_text)
    if dec_match:
        num = dec_match.group(1)
        title, _ = _extract_title_from_rest(dec_match.group(2))
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=num,
            number_type="decimal",
            title=title,
        )

    # 5. Explicit "Clause 1", "Section 1.1"
    explicit_match = _EXPLICIT_CLAUSE_RE.match(line_text)
    if explicit_match:
        num = explicit_match.group(1)
        title, _ = _extract_title_from_rest(explicit_match.group(2))
        num_type = "decimal" if "." in num else "integer"
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=num,
            number_type=num_type,
            title=title,
        )

    # 6. Single integer dot (e.g. "1. DEFINITIONS", "2. GRANT")
    int_match = _INTEGER_NUMBER_RE.match(line_text)
    if int_match:
        num = int_match.group(1)
        title, _ = _extract_title_from_rest(int_match.group(2))
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=num,
            number_type="integer",
            title=title,
        )

    # 7. Roman numerals (e.g. "(i)", "i.")
    roman_sub = _ROMAN_SUBCLAUSE_RE.match(line_text)
    if roman_sub:
        num_str = roman_sub.group(1).lower()
        title, _ = _extract_title_from_rest(roman_sub.group(2))
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=f"({num_str})",
            number_type="roman",
            title=title,
        )

    roman_dot = _ROMAN_DOT_RE.match(line_text)
    if roman_dot:
        num_str = roman_dot.group(1).lower()
        title, _ = _extract_title_from_rest(roman_dot.group(2))
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=f"({num_str})",
            number_type="roman",
            title=title,
        )

    # 8. Parenthesized subclause (e.g. "(a)", "(b)", "(1)")
    paren_match = _PAREN_SUBCLAUSE_RE.match(line_text)
    if paren_match:
        num_str = paren_match.group(1)
        title, _ = _extract_title_from_rest(paren_match.group(2))
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=f"({num_str})",
            number_type="paren",
            title=title,
        )

    # 9. Letter dot (e.g. "a. ", "b. ")
    letter_dot = _LETTER_DOT_RE.match(line_text)
    if letter_dot:
        num_str = letter_dot.group(1)
        title, _ = _extract_title_from_rest(letter_dot.group(2))
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=f"({num_str})",
            number_type="paren",
            title=title,
        )

    # 10. Recital capital letter (e.g. "(A) ")
    recital_letter = _RECITAL_LETTER_RE.match(line_text)
    if recital_letter:
        num_str = recital_letter.group(1)
        return _LineInfo(
            start_offset=line_start,
            end_offset=line_end,
            text=line_text,
            is_boundary=True,
            is_section_boundary=False,
            new_section=None,
            number=f"({num_str})",
            number_type="recital",
            title=None,
        )

    # 11. Standalone all-caps heading
    caps_match = _ALL_CAPS_HEADING_RE.match(line_text)
    if caps_match:
        heading = caps_match.group(1).strip()
        if heading.upper() not in _STOP_HEADINGS and len(heading.split()) <= 8:
            return _LineInfo(
                start_offset=line_start,
                end_offset=line_end,
                text=line_text,
                is_boundary=True,
                is_section_boundary=False,
                new_section=None,
                number=None,
                number_type="heading",
                title=heading,
            )

    return _LineInfo(
        start_offset=line_start,
        end_offset=line_end,
        text=line_text,
        is_boundary=False,
        is_section_boundary=False,
        new_section=None,
        number=None,
        number_type=None,
        title=None,
    )


def _compute_clause_pages(
    start_offset: int,
    end_offset: int,
    pages_meta: list[PageText],
) -> list[int]:
    """Calculate the list of 1-indexed page numbers overlapping a clause offset range."""
    touched: list[int] = []
    for p in pages_meta:
        if not p.has_text:
            continue
        # Overlap of [start_offset, end_offset) with [p.start_offset, p.end_offset)
        if max(start_offset, p.start_offset) < min(end_offset, p.end_offset):
            touched.append(p.page_number)

    if not touched:
        # Fallback to nearest page or page 1
        for p in pages_meta:
            if p.start_offset <= start_offset <= p.end_offset:
                return [p.page_number]
        return [1]

    return sorted(touched)


def _extract_defined_terms(
    full_text: str,
    clauses: list[Clause],
    pages_meta: list[PageText],
) -> tuple[dict[str, str], list[DefinedTerm]]:
    """Extract defined terms and definitions from parsed clauses and text.

    Args:
        full_text: The complete document text.
        clauses: List of segmented clauses.
        pages_meta: Metadata for pages to calculate provenance.

    Returns:
        Tuple of (defined_terms_dict, detailed_defined_terms_list).
    """
    defined_terms_dict: dict[str, str] = {}
    detailed_terms: list[DefinedTerm] = []
    seen_terms_lower: set[str] = set()

    # Pattern for explicit definitions: "Term" means / shall mean / : / - ...
    explicit_pattern = re.compile(
        r"""(?P<quote>["“'‘])(?P<term>[A-Za-z0-9\s\-_/&]+)(?P=quote)\s*"""
        r"""(?P<connector>means|shall\s+mean|has\s+the\s+meaning|refers\s+to|:|—|–|-)\s*"""
        r"""(?P<definition>.*?)(?:;|\.\s*(?:\n|\Z)|\n\s*["“'‘]|\Z)""",
        re.DOTALL | re.IGNORECASE,
    )

    # Pattern for inline parenthetical definitions: ... (the "Term")
    inline_pattern = re.compile(
        r"""(?P<preceding>[^.;\n]{2,100}?)\s*"""
        r"""\((?:(?:hereinafter\s+)?(?:referred\s+to\s+as\s+|called\s+)?(?:the\s+|each\s+an?\s+|collectively\s+the\s+)?|the\s+)"""
        r"""(?P<quote>["“'‘])(?P<term>[A-Za-z0-9\s\-_/&]+)(?P=quote)\)""",
        re.IGNORECASE,
    )

    for clause in clauses:
        clause_text = clause.text

        # 1. Check for explicit definitions in this clause
        for m in explicit_pattern.finditer(clause_text):
            raw_term = m.group("term").strip()
            raw_def = m.group("definition").strip()
            connector = m.group("connector").strip()

            if not raw_term or len(raw_term) > 60 or not raw_def:
                continue

            # Format definition text
            if connector.lower() in ("means", "shall mean", "has the meaning", "refers to"):
                definition = f"{connector} {raw_def}"
            else:
                definition = raw_def

            term_key = raw_term
            term_lower = term_key.lower()

            local_start = m.start()
            local_end = m.end()
            global_start = clause.start_offset + local_start
            global_end = clause.start_offset + local_end
            pages = _compute_clause_pages(global_start, global_end, pages_meta)

            if term_lower not in seen_terms_lower:
                seen_terms_lower.add(term_lower)
                defined_terms_dict[term_key] = definition
                detailed_terms.append(
                    DefinedTerm(
                        term=term_key,
                        definition=definition,
                        clause_id=clause.clause_id,
                        pages=pages,
                        start_offset=global_start,
                        end_offset=global_end,
                    )
                )

        # 2. Check for inline parenthetical definitions
        for m in inline_pattern.finditer(clause_text):
            raw_term = m.group("term").strip()
            preceding = m.group("preceding").strip()

            if not raw_term or len(raw_term) > 60 or not preceding:
                continue

            # Clean preceding antecedent: strip leading prepositions/articles
            preceding_clean = re.sub(
                r"^(?:between|and|to|with|for|from|by|in)\s+",
                "",
                preceding,
                flags=re.IGNORECASE,
            ).strip()

            term_key = raw_term
            term_lower = term_key.lower()

            if term_lower not in seen_terms_lower:
                seen_terms_lower.add(term_lower)
                definition = preceding_clean
                defined_terms_dict[term_key] = definition

                local_start = m.start()
                local_end = m.end()
                global_start = clause.start_offset + local_start
                global_end = clause.start_offset + local_end
                pages = _compute_clause_pages(global_start, global_end, pages_meta)

                detailed_terms.append(
                    DefinedTerm(
                        term=term_key,
                        definition=definition,
                        clause_id=clause.clause_id,
                        pages=pages,
                        start_offset=global_start,
                        end_offset=global_end,
                    )
                )

    return defined_terms_dict, detailed_terms


def segment_document(document: ExtractedDocument) -> SegmentedDocument:
    """Split an ExtractedDocument into clauses, preserving offsets and extracting defined terms.

    Splits the contract into structured, non-overlapping clauses keeping character offsets
    such that full_text[start_offset:end_offset] == clause_text for every clause.
    Schedules and annexes are maintained as distinct sections.

    Args:
        document: ExtractedDocument from mbiu.documents.extract.

    Returns:
        SegmentedDocument containing parsed clauses, defined terms, and sections.
    """
    full_text = document.full_text
    if not full_text or not full_text.strip():
        return SegmentedDocument(
            clauses=[],
            defined_terms={},
            defined_terms_detailed=[],
            sections=[],
            total_clauses=0,
        )

    # 1. Break full_text into lines with character spans
    raw_lines: list[tuple[int, int, str]] = []
    for m in re.finditer(r"[^\r\n]*(?:\r\n|\r|\n)?", full_text):
        if m.start() == m.end():
            continue
        raw_lines.append((m.start(), m.end(), m.group()))

    classified_lines: list[_LineInfo] = [
        _classify_line(start, end, text) for start, end, text in raw_lines
    ]

    has_structural_elements = any(
        line.is_boundary for line in classified_lines if line.text.strip()
    )

    # Group lines into clause blocks
    # A block is a list of LineInfo objects
    blocks: list[list[_LineInfo]] = []
    current_block: list[_LineInfo] = []

    # Hierarchy and naming state
    current_section = "main"
    has_seen_numbered_clause = False

    seen_first_boundary = False

    for line in classified_lines:
        is_empty = not line.text.strip()

        if line.is_section_boundary:
            seen_first_boundary = True
            # Flush current block if any non-empty content exists
            if current_block and any(blk_line.text.strip() for blk_line in current_block):
                blocks.append(current_block)
                current_block = []
            current_section = line.new_section or current_section
            current_block.append(line)
            continue

        if line.is_boundary:
            # Allow opening document title heading at the very start to form the preamble block
            if not seen_first_boundary and not current_block and line.number_type == "heading":
                current_block.append(line)
                continue

            seen_first_boundary = True
            has_seen_numbered_clause = True
            # Flush current block
            if current_block and any(blk_line.text.strip() for blk_line in current_block):
                blocks.append(current_block)
                current_block = []
            current_block.append(line)
            continue

        # If document has no structural numbering/headings, split on blank line transitions
        if not has_structural_elements and is_empty:
            if current_block and any(blk_line.text.strip() for blk_line in current_block):
                blocks.append(current_block)
                current_block = []
            continue

        # If we have not yet seen any numbered clause and we are at the top,
        # preamble lines accumulate until the first structural boundary
        current_block.append(line)

    if current_block and any(blk_line.text.strip() for blk_line in current_block):
        blocks.append(current_block)

    # 2. Build Clause instances from blocks while assigning unique hierarchical IDs
    clauses: list[Clause] = []
    seen_clause_ids: set[str] = set()
    distinct_sections: list[str] = []

    active_section = "main" if has_seen_numbered_clause else "Preamble"
    current_parent_num: str | None = None
    current_letter_parent: str | None = None

    for block_idx, block in enumerate(blocks):
        # Determine exact raw offsets for this block
        raw_start = block[0].start_offset
        raw_end = block[-1].end_offset
        raw_slice = full_text[raw_start:raw_end]

        stripped = raw_slice.strip()
        if not stripped:
            continue

        # Calculate exact whitespace shifts to preserve full_text[start:end] == clause_text
        leading_ws = len(raw_slice) - len(raw_slice.lstrip())
        trailing_ws = len(raw_slice) - len(raw_slice.rstrip())

        clause_start = raw_start + leading_ws
        clause_end = raw_end - trailing_ws
        clause_text = full_text[clause_start:clause_end]

        # Determine section, title, and numbering from the block's first line
        first_line = block[0]
        if first_line.is_section_boundary and first_line.new_section:
            active_section = first_line.new_section
        elif block_idx == 0:
            if first_line.number_type not in ("decimal", "integer"):
                active_section = "Preamble"
            else:
                active_section = "main"
        elif active_section in ("Preamble", "Recitals") and first_line.number_type in (
            "decimal",
            "integer",
            "heading",
        ):
            active_section = "main"

        if active_section not in distinct_sections:
            distinct_sections.append(active_section)

        # Clause title determination
        clause_title = first_line.title

        # Determine hierarchical clause ID
        is_schedule = (
            "schedule" in active_section.lower()
            or "annex" in active_section.lower()
            or "exhibit" in active_section.lower()
            or "appendix" in active_section.lower()
        )
        schedule_prefix = f"{_clean_slug(active_section)}_" if is_schedule else ""

        base_id: str
        if first_line.is_section_boundary:
            base_id = f"{schedule_prefix}header" if is_schedule else _clean_slug(active_section)
            current_parent_num = None
            current_letter_parent = None
        elif block_idx == 0 and active_section == "Preamble":
            base_id = "preamble"
            current_parent_num = None
            current_letter_parent = None
        elif first_line.number_type == "decimal" and first_line.number:
            base_id = f"{schedule_prefix}{first_line.number}"
            current_parent_num = first_line.number
            current_letter_parent = None
        elif first_line.number_type == "integer" and first_line.number:
            base_id = f"{schedule_prefix}{first_line.number}"
            current_parent_num = first_line.number
            current_letter_parent = None
        elif first_line.number_type == "paren" and first_line.number:
            parent = current_parent_num or ""
            base_id = (
                f"{schedule_prefix}{parent}{first_line.number}"
                if parent
                else f"{schedule_prefix}{first_line.number}"
            )
            current_letter_parent = base_id
        elif first_line.number_type == "roman" and first_line.number:
            parent = current_letter_parent or current_parent_num or ""
            base_id = (
                f"{parent}{first_line.number}"
                if parent
                else f"{schedule_prefix}{first_line.number}"
            )
        elif first_line.number_type == "recital" and first_line.number:
            letter = first_line.number.strip("()")
            base_id = f"recital_{letter}"
        elif first_line.number_type == "heading" and first_line.title:
            slug = _clean_slug(first_line.title)
            base_id = f"{schedule_prefix}{slug}"
            current_parent_num = slug
            current_letter_parent = None
        else:
            # Unnumbered block
            base_id = (
                f"{schedule_prefix}clause_{len(clauses) + 1}"
                if is_schedule
                else f"clause_{len(clauses) + 1}"
            )

        # Long schedule titles and headings would pass the API's 64-character limit;
        # 56 leaves room for the "_NN" suffix below
        base_id = base_id[:56].rstrip("_")

        # Deduplicate clause_id to guarantee uniqueness across the document
        clause_id = base_id
        if clause_id in seen_clause_ids:
            counter = 2
            while f"{clause_id}_{counter}" in seen_clause_ids:
                counter += 1
            clause_id = f"{clause_id}_{counter}"
        seen_clause_ids.add(clause_id)

        # Calculate touched pages
        pages = _compute_clause_pages(clause_start, clause_end, document.pages)

        clauses.append(
            Clause(
                clause_id=clause_id,
                section=active_section,
                title=clause_title,
                text=clause_text,
                pages=pages,
                start_offset=clause_start,
                end_offset=clause_end,
            )
        )

    # 3. Extract defined terms map
    defined_terms_dict, detailed_terms = _extract_defined_terms(
        full_text=full_text,
        clauses=clauses,
        pages_meta=document.pages,
    )

    return SegmentedDocument(
        clauses=clauses,
        defined_terms=defined_terms_dict,
        defined_terms_detailed=detailed_terms,
        sections=distinct_sections,
        total_clauses=len(clauses),
    )


def segment_text(
    full_text: str,
    *,
    page_count: int = 1,
) -> SegmentedDocument:
    """Split raw text into clauses and extract defined terms.

    Convenience helper for reference corpus templates or in-memory strings.
    Synthesizes an ExtractedDocument with pages spanning the text length.

    Args:
        full_text: Raw contract text string.
        page_count: Number of simulated pages (default 1).

    Returns:
        SegmentedDocument with segmented clauses and defined terms map.
    """
    if not full_text or not full_text.strip():
        return SegmentedDocument(
            clauses=[],
            defined_terms={},
            defined_terms_detailed=[],
            sections=[],
            total_clauses=0,
        )

    text_len = len(full_text)
    pages: list[PageText] = []

    if page_count <= 1:
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
        chunk_size = text_len // page_count
        current_offset = 0
        for i in range(page_count):
            end_offset = text_len if i == page_count - 1 else current_offset + chunk_size
            page_str = full_text[current_offset:end_offset]
            pages.append(
                PageText(
                    page_number=i + 1,
                    text=page_str,
                    start_offset=current_offset,
                    end_offset=end_offset,
                    has_text=bool(page_str.strip()),
                )
            )
            current_offset = end_offset

    doc = ExtractedDocument(
        pages=pages,
        full_text=full_text,
        total_pages=len(pages),
        skipped_pages=[],
    )

    return segment_document(doc)
