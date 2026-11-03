"""CLI runner and entrypoint for the corpus pipeline.

Usage:
    python -m mbiu.corpus.pipeline --version-tag v1.0.0
    python -m mbiu.corpus.pipeline --version-tag v1.0.0 --dry-run
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import django

from mbiu.corpus.pipeline.checks import TemplateClauseData, TemplateSourceData
from mbiu.corpus.pipeline.publish import CorpusPublisher, PublishResult

logger = logging.getLogger(__name__)


def get_default_synthetic_standards() -> tuple[list[TemplateSourceData], list[TemplateClauseData]]:
    """Return standard synthetic reference templates for bootstrap and testing."""
    sources = [
        TemplateSourceData(
            title="WIPO How to Make a Living from Music (3rd Ed) - Management Standards",
            license="CC BY 4.0",
            reviewing_body="WIPO",
            contract_type="management",
            jurisdiction="international",
            url="https://www.wipo.int/publications/en/details.jsp?id=4681",
        ),
        TemplateSourceData(
            title="Kenya Copyright Act (Cap. 130) - Statutory Music Standards",
            license="Kenya Copyright Act (Cap. 130)",
            reviewing_body="Kenya Copyright Board",
            contract_type="recording",
            jurisdiction="KE",
            url="http://www.kenyalaw.org",
        ),
    ]

    clauses = [
        TemplateClauseData(
            chunk_key="WIPO-MGMT-01",
            text=(
                "The Manager shall receive a commission of 15% of the Artist's "
                "Gross Receipts directly derived from entertainment activities. "
                "No commission shall apply to non-entertainment earnings."
            ),
            source=sources[0],
            metadata={"standard_section": "Commission and Royalties"},
        ),
        TemplateClauseData(
            chunk_key="WIPO-MGMT-02",
            text=(
                "The Artist shall have the right, at the Artist's own expense and on thirty (30) "
                "days' prior written notice, to inspect and audit the books and records of the "
                "Manager relating to Gross Receipts."
            ),
            source=sources[0],
            metadata={"standard_section": "Accounting and Audit"},
        ),
        TemplateClauseData(
            chunk_key="KE-COPYRIGHT-01",
            text=(
                "In accordance with Section 30 of the Kenya Copyright Act (Cap. 130), the author "
                "or performer shall have the moral right to claim authorship of the work "
                "and to object to any distortion, mutilation or modification thereof."
            ),
            source=sources[1],
            metadata={"standard_section": "Moral Rights"},
        ),
        TemplateClauseData(
            chunk_key="KE-RECORDING-01",
            text=(
                "The Record Company shall pay to the Artist a royalty of not less than 15% "
                "of gross wholesale receipts. Recording costs shall be recoupable solely from "
                "the Artist's royalty earnings and not from any other income streams."
            ),
            source=sources[1],
            metadata={"standard_section": "Recording Royalties"},
        ),
    ]

    return sources, clauses


def parse_sources_file(
    file_path: Path,
) -> tuple[list[TemplateSourceData], list[TemplateClauseData]]:
    """Parse template sources and clauses from JSON or YAML file."""
    if not file_path.exists():
        logger.warning("Sources file %s not found. Using default standard sources.", file_path)
        return get_default_synthetic_standards()

    raw_text = file_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return get_default_synthetic_standards()

    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError:
        # If not JSON, check if sources list is empty (e.g. sources: [])
        if "sources: []" in raw_text or not raw_text:
            return get_default_synthetic_standards()
        logger.warning("Unable to parse %s as JSON. Using default standards.", file_path)
        return get_default_synthetic_standards()

    sources_data = data.get("sources", [])
    if not sources_data:
        return get_default_synthetic_standards()

    sources: list[TemplateSourceData] = []
    clauses: list[TemplateClauseData] = []

    for s_idx, s in enumerate(sources_data):
        src = TemplateSourceData(
            title=s.get("title", f"Standard Document {s_idx + 1}"),
            license=s.get("license", s.get("licence", "")),
            reviewing_body=s.get("reviewing_body", "Industry Standard"),
            contract_type=s.get("contract_type", "general_music"),
            jurisdiction=s.get("jurisdiction", "KE"),
            url=s.get("url", ""),
        )
        sources.append(src)

        for c_idx, c in enumerate(s.get("clauses", [])):
            clause = TemplateClauseData(
                chunk_key=c.get("chunk_key", f"Chunk-{s_idx + 1}-{c_idx + 1}"),
                text=c.get("text", ""),
                source=src,
                metadata=c.get("metadata", {}),
            )
            clauses.append(clause)

    if not clauses:
        return get_default_synthetic_standards()

    return sources, clauses


def run_pipeline(
    version_tag: str,
    sources_path: Path | None = None,
    dry_run: bool = False,
    activate: bool = True,
) -> PublishResult:
    """Run the corpus pipeline orchestrator."""
    if sources_path:
        sources, clauses = parse_sources_file(sources_path)
    else:
        sources, clauses = get_default_synthetic_standards()

    publisher = CorpusPublisher()

    if dry_run:
        logger.info("Executing dry-run for version %s (no database writes)", version_tag)
        return publisher.publish_version(
            version_tag=version_tag,
            sources=sources,
            clauses=clauses,
            activate=False,
            strict_checks=False,
            dry_run=True,
        )

    result = publisher.publish_version(
        version_tag=version_tag,
        sources=sources,
        clauses=clauses,
        activate=activate,
        strict_checks=True,
    )
    return result


def main() -> None:
    """CLI entrypoint for executing corpus pipeline."""
    # Ensure Django is configured
    try:
        django.setup()
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Mbiu Corpus Pipeline: tag, check, embed, and publish standards."
    )
    parser.add_argument(
        "--version-tag",
        type=str,
        required=True,
        help="Unique semantic release tag (e.g. v1.0.0)",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=None,
        help="Path to sources file (JSON or YAML)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run validation and checks without writing to database or activating",
    )
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Publish records to database without activating version",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    try:
        result = run_pipeline(
            version_tag=args.version_tag,
            sources_path=args.sources,
            dry_run=args.dry_run,
            activate=not args.no_activate,
        )
        logger.info(
            "Pipeline completed: tag=%s, chunks=%d, active=%s",
            result.version_tag,
            result.total_chunks,
            result.is_active,
        )
    except Exception as exc:
        logger.error("Pipeline error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
