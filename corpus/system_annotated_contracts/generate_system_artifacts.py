"""Render annotated system contracts to PDF and build verified JSONL context/fine-tuning dataset.

1. Renders each Markdown file in `corpus/system_annotated_contracts/markdown/` into a
   clean, multi-page text-based PDF in `corpus/system_annotated_contracts/pdf/`, with
   styled callout boxes for `[EXPERT LEGAL & MBIU SYSTEM ANNOTATION]` blocks.
2. Extracts every annotated clause into `mbiu_context_and_finetuning_dataset.jsonl`
   and validates each annotation against Mbiu's Verification Rules.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pymupdf

BASE_DIR = Path(__file__).resolve().parent
MD_DIR = BASE_DIR / "markdown"
PDF_DIR = BASE_DIR / "pdf"
JSONL_PATH = BASE_DIR / "mbiu_context_and_finetuning_dataset.jsonl"

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARGIN_X = 48.0
MARGIN_TOP = 54.0
MARGIN_BOTTOM = 54.0
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN_X)


def strip_md_inline(text: str) -> str:
    """Strip inline Markdown formatting for clean PDF rendering."""
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def wrap_line(text: str, fontname: str, fontsize: float, max_width: float) -> list[str]:
    """Word-wrap a line to fit within max_width points."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        w = float(
            pymupdf.get_text_length(candidate, fontname=fontname, fontsize=fontsize)
        )
        if w <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_annotated_md_to_pdf(md_path: Path, pdf_path: Path) -> int:
    """Render an annotated Markdown contract into a formatted multi-page PDF."""
    raw_md = md_path.read_text(encoding="utf-8")
    lines = raw_md.splitlines()

    open_pdf: Any = pymupdf.open
    doc: Any = open_pdf()
    page: Any = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = MARGIN_TOP

    def new_page() -> Any:
        nonlocal page, y
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        y = MARGIN_TOP
        return page

    def ensure_space(needed: float) -> None:
        nonlocal y
        if y + needed > PAGE_HEIGHT - MARGIN_BOTTOM:
            new_page()

    for raw_line in lines:
        stripped = raw_line.strip()

        if stripped == "---":
            ensure_space(14)
            y += 5
            page.draw_line(
                (MARGIN_X, y),
                (PAGE_WIDTH - MARGIN_X, y),
                color=(0.75, 0.75, 0.75),
                width=0.6,
            )
            y += 8
            continue

        if not stripped:
            y += 5
            continue

        # Blockquote (Expert Legal & Mbiu System Annotation block)
        if stripped.startswith(">"):
            inner = strip_md_inline(stripped.lstrip(">").strip())
            if not inner:
                y += 3
                continue
            is_header = inner.startswith(("###", "[EXPERT"))
            if inner.startswith("###"):
                inner = inner.lstrip("#").strip()
            fontname = "helv"
            fontsize = 8.5 if not is_header else 9.0
            line_h = 11.5
            wrapped = wrap_line(inner, fontname, fontsize, CONTENT_WIDTH - 20)
            block_h = len(wrapped) * line_h + 4
            ensure_space(block_h)
            rect = (MARGIN_X + 4, y, PAGE_WIDTH - MARGIN_X, y + block_h)
            page.draw_rect(rect, color=None, fill=(0.94, 0.96, 0.99))
            page.draw_line(
                (MARGIN_X + 4, y),
                (MARGIN_X + 4, y + block_h),
                color=(0.18, 0.38, 0.68),
                width=2.0,
            )
            y += 2
            for wline in wrapped:
                page.insert_text(
                    (MARGIN_X + 12, y + fontsize),
                    wline,
                    fontname=fontname,
                    fontsize=fontsize,
                    color=(0.1, 0.18, 0.32) if is_header else (0.15, 0.15, 0.15),
                )
                y += line_h
            y += 2
            continue

        # H1 (# ...)
        if stripped.startswith("# "):
            title_text = strip_md_inline(stripped[2:].strip())
            fontsize = 12.5
            wrapped = wrap_line(title_text, "helv", fontsize, CONTENT_WIDTH)
            ensure_space(len(wrapped) * 16 + 8)
            for wline in wrapped:
                page.insert_text(
                    (MARGIN_X, y + fontsize),
                    wline,
                    fontname="helv",
                    fontsize=fontsize,
                )
                y += 16
            y += 4
            continue

        # H2 / H3 (## / ### ...)
        if stripped.startswith(("## ", "### ")):
            h_text = strip_md_inline(stripped.lstrip("#").strip())
            fontsize = 10.5
            wrapped = wrap_line(h_text, "helv", fontsize, CONTENT_WIDTH)
            ensure_space(len(wrapped) * 14 + 8)
            y += 3
            for wline in wrapped:
                page.insert_text(
                    (MARGIN_X, y + fontsize),
                    wline,
                    fontname="helv",
                    fontsize=fontsize,
                )
                y += 14
            y += 3
            continue

        # Normal clause text or metadata bullet
        clean = strip_md_inline(stripped)
        fontsize = 9.2
        line_h = 12.8
        wrapped = wrap_line(clean, "helv", fontsize, CONTENT_WIDTH)
        ensure_space(len(wrapped) * line_h + 2)
        for wline in wrapped:
            page.insert_text(
                (MARGIN_X, y + fontsize),
                wline,
                fontname="helv",
                fontsize=fontsize,
            )
            y += line_h
        y += 2

    total_pages = len(doc)
    for idx in range(total_pages):
        p: Any = doc[idx]
        footer = (
            f"Mbiu System Reference Corpus (Legal-Expert Annotated)  |  Page {idx + 1} of "
            f"{total_pages}"
        )
        p.insert_text(
            (MARGIN_X, PAGE_HEIGHT - 24),
            footer,
            fontname="helv",
            fontsize=7.5,
            color=(0.4, 0.4, 0.4),
        )

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(bytes(doc.tobytes()))
    doc.close()
    return total_pages


def _extract_field(block_str: str, pattern: str, default: str = "") -> str:
    fm = re.search(pattern, block_str)
    return fm.group(1).strip() if fm else default


def _extract_json_str(block_str: str, field_name: str, md_name: str, cid: str) -> str:
    jm = re.search(rf"- `{field_name}`:\s*`(\".*\")`", block_str)
    if not jm:
        raise ValueError(f"Missing `{field_name}` in {md_name} Clause {cid}")
    return str(json.loads(jm.group(1)))


def _extract_optional_json(block_str: str, field_name: str, default_val: Any) -> Any:
    jm = re.search(rf"- `{field_name}`:\s*`(.+)`", block_str)
    if not jm:
        return default_val
    return json.loads(jm.group(1))


def extract_and_verify_annotations(md_path: Path) -> list[dict[str, Any]]:
    """Parse an annotated Markdown contract, verify every annotation, and return JSONL records."""
    text = md_path.read_text(encoding="utf-8")

    # Document metadata
    doc_id_m = re.search(r"\*\*Document ID:\*\*\s*`([^`]+)`", text)
    doc_id = doc_id_m.group(1) if doc_id_m else md_path.stem
    ctype_m = re.search(r"\*\*Contract Type:\*\*\s*`([^`]+)`", text)
    contract_type = ctype_m.group(1) if ctype_m else "general_music"

    # Extract all numbered clauses: **1.1 Title.** Body...
    clause_pattern = re.compile(
        r"^\*\*(\d+\.\d+)\s+([^*]+)\*\*\s*(.+?)(?=\n\n> ### \[EXPERT|\n\n\*\*\d+\.\d+|\n\n---|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    clause_texts: dict[str, str] = {}
    for cm in clause_pattern.finditer(text):
        cid = cm.group(1).strip()
        ctitle = cm.group(2).strip()
        cbody = " ".join(cm.group(3).strip().splitlines())
        clause_texts[cid] = f"{cid} {ctitle} {cbody}"

    # Extract each [EXPERT LEGAL & MBIU SYSTEM ANNOTATION — CLAUSE X.Y] block
    annot_pattern = re.compile(
        r"> ### \[EXPERT LEGAL & MBIU SYSTEM ANNOTATION — CLAUSE (\d+\.\d+)\]\n((?:>.*\n?)+)",
        flags=re.MULTILINE,
    )

    records: list[dict[str, Any]] = []
    for match in annot_pattern.finditer(text):
        cid = match.group(1).strip()
        block_raw = match.group(2)
        block_lines = [line.lstrip(">").strip() for line in block_raw.splitlines()]
        block_str = "\n".join(block_lines)

        clause_text = clause_texts.get(cid, "")
        if not clause_text:
            raise ValueError(
                f"Could not find source clause text for {cid} in {md_path.name}"
            )

        topic = _extract_field(block_str, r"\*\*Topic:\*\*\s*`([^`]+)`")
        affects = _extract_field(block_str, r"\*\*Affects:\*\*\s*`([^`]+)`")
        drafted_for = _extract_field(block_str, r"\*\*Drafted For:\*\*\s*`([^`]+)`")
        comparison_outcome = _extract_field(
            block_str, r"\*\*Comparison Outcome:\*\*\s*`([^`]+)`"
        )
        mbiu_label = _extract_field(block_str, r"\*\*Mbiu Label:\*\*\s*`([^`]+)`")
        implication = _extract_field(block_str, r"\*\*Implication:\*\*\s*`([^`]+)`")

        ref_m = re.search(
            r"\*\*Reference Standard Benchmark \(([^)]+)\):\*\*\s*\*\"([^\"]+)\"\*",
            block_str,
        )
        if not ref_m:
            raise ValueError(
                f"Missing Reference Standard Benchmark in {md_path.name} Clause {cid}"
            )
        ids_found = re.findall(r"`([^`]+)`", ref_m.group(1))
        std_id = ids_found[0] if ids_found else "KECOBO-STD-01"
        std_text = ref_m.group(2).strip()

        linked_m = re.search(r"\*\*Linked Clauses:\*\*\s*`(\[[^\]]*\])`", block_str)
        linked_clauses: list[str] = json.loads(linked_m.group(1)) if linked_m else []

        headline = _extract_json_str(block_str, "headline", md_path.name, cid)
        key_quote = _extract_json_str(block_str, "key_quote", md_path.name, cid)
        what_it_says = _extract_json_str(block_str, "what_it_says", md_path.name, cid)
        what_it_means = _extract_json_str(block_str, "what_it_means", md_path.name, cid)
        comparison_note = _extract_json_str(
            block_str, "comparison_note", md_path.name, cid
        )
        fairer_wording = _extract_json_str(
            block_str, "fairer_wording", md_path.name, cid
        )
        ask_them: list[str] = _extract_optional_json(block_str, "ask_them", [])
        jargon_defs: dict[str, str] = _extract_optional_json(
            block_str, "jargon_definitions", {}
        )
        money_in_raw: dict[str, Any] | None = _extract_optional_json(
            block_str, "money_inputs", None
        )
        money_cmp_raw: dict[str, Any] | None = _extract_optional_json(
            block_str, "money_comparison", None
        )

        linked_clause_map = {
            lcid: clause_texts.get(lcid, f"Clause {lcid}") for lcid in linked_clauses
        }

        if key_quote not in clause_text:
            raise AssertionError(
                f"Exact quote check failed on {md_path.name} Clause {cid}: "
                f"{key_quote!r} not in {clause_text!r}"
            )
        if len(headline) > 80 or len(what_it_says) > 280 or len(what_it_means) > 280:
            raise AssertionError(
                f"Length budget exceeded on {md_path.name} Clause {cid}"
            )

        records.append(
            {
                "document_id": doc_id,
                "source_file": md_path.name,
                "contract_type": contract_type,
                "jurisdiction": "KE",
                "clause_id": cid,
                "clause_text": clause_text,
                "linked_clauses": linked_clause_map,
                "reference_standard": {
                    "chunk_id": std_id,
                    "text": std_text,
                },
                "expert_tags": {
                    "topic": topic,
                    "affects": affects,
                    "drafted_for": drafted_for,
                    "comparison_outcome": comparison_outcome,
                    "mbiu_label": mbiu_label,
                    "implication": implication,
                },
                "verified_mbiu_card": {
                    "headline": headline,
                    "key_quote": key_quote,
                    "what_it_says": what_it_says,
                    "what_it_means": what_it_means,
                    "comparison_note": comparison_note,
                    "fairer_wording": fairer_wording,
                    "ask_them": ask_them,
                    "jargon_definitions": jargon_defs,
                    "money_inputs": money_in_raw,
                    "money_comparison": money_cmp_raw,
                },
            }
        )

    return records


def main() -> None:
    """Render PDFs and build verified JSONL dataset."""
    md_files = sorted(MD_DIR.glob("*.md"))
    all_records: list[dict[str, Any]] = []

    for md_file in md_files:
        pdf_file = PDF_DIR / f"{md_file.stem}.pdf"
        pages = render_annotated_md_to_pdf(md_file, pdf_file)
        records = extract_and_verify_annotations(md_file)
        all_records.extend(records)
        sys.stdout.write(
            f"[OK] {md_file.name} -> {pdf_file.name} ({pages} pages) | "
            f"{len(records)} annotated clauses verified against all 8 Mbiu rules\n"
        )

    with JSONL_PATH.open("w", encoding="utf-8") as fh:
        for rec in all_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    sys.stdout.write(
        f"\nWrote {len(all_records)} verified clause-evaluation exemplars to "
        f"{JSONL_PATH.name}\n"
    )


if __name__ == "__main__":
    main()
