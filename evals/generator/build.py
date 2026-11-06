"""Build the synthetic golden set.

Usage::

    python -m evals.generator.build
    python -m evals.generator.build --out /tmp/golden-set

Every contract starts from the reviewed recording template. Risks are planted
by replacing specific clauses, so the expected outcome is known by construction
and needs no human labelling. The output is a PDF plus a JSON sidecar per
contract, a JSONL index, Promptfoo test cases, and a manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from evals.generator import GENERATOR_VERSION, SCHEMA_VERSION
from evals.generator.jsonutil import dump_json
from evals.generator.models import (
    ClauseExpectation,
    GoldenContract,
    PlantedRisk,
    TemplateClause,
)
from evals.generator.pdf import render_contract
from evals.generator.reference_evaluator import lenient_prediction
from evals.generator.risks import RISK_DEFINITIONS_BY_ID, RiskDefinition, RiskKind
from evals.generator.schema import GOLDEN_CONTRACT_SCHEMA, PREDICTION_SCHEMA
from evals.generator.templates import (
    CONTRACT_TYPE,
    JURISDICTION,
    STANDARD_CLAUSES,
    STANDARD_TEMPLATE_ID,
    clause_block,
)
from evals.generator.variants import VARIANTS, ContractVariant

EVALS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = EVALS_DIR / "datasets"


@dataclass(frozen=True)
class BuildResult:
    """Where the dataset was written and what it contains."""

    dataset_dir: Path
    contracts: tuple[GoldenContract, ...]
    files_written: tuple[Path, ...]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _risk_pages(
    risk: RiskDefinition, clause_pages: dict[str, tuple[int, ...]]
) -> tuple[int, ...]:
    pages: list[int] = []
    for clause_id in risk.clause_ids:
        pages.extend(clause_pages[clause_id])
    return tuple(dict.fromkeys(pages))


def _expectations(
    variant: ContractVariant,
    clause_pages: dict[str, tuple[int, ...]],
) -> tuple[tuple[ClauseExpectation, ...], tuple[PlantedRisk, ...]]:
    outcomes: dict[str, str] = {
        clause.clause_id: "matches_standard" for clause in variant.clauses()
    }
    planted: dict[str, list[str]] = {
        clause.clause_id: [] for clause in variant.clauses()
    }
    conflicts: dict[str, list[str]] = {
        clause.clause_id: [] for clause in variant.clauses()
    }
    risks: list[PlantedRisk] = []

    for risk_id in variant.risk_ids:
        definition = RISK_DEFINITIONS_BY_ID[risk_id]
        for clause_id in definition.clause_ids:
            if definition.kind == "cross_clause":
                conflicts[clause_id].append(
                    definition.expected_issue_kind or risk_id.value
                )
                outcomes[clause_id] = "worse_for_you"
            else:
                planted[clause_id].append(risk_id.value)
                outcomes[clause_id] = definition.expected_outcome or "worse_for_you"
        risks.append(
            PlantedRisk(
                risk_id=risk_id.value,
                kind=definition.kind,
                description=definition.description,
                clause_ids=definition.clause_ids,
                pages=_risk_pages(definition, clause_pages),
                expected_outcome=definition.expected_outcome,
                expected_issue_kind=definition.expected_issue_kind,
            )
        )

    clauses = tuple(
        ClauseExpectation(
            clause_id=clause.clause_id,
            heading=clause.heading,
            pages=clause_pages[clause.clause_id],
            text=clause.text,
            expected_outcome=outcomes[clause.clause_id],
            planted_risk_ids=tuple(planted[clause.clause_id]),
            conflict_ids=tuple(conflicts[clause.clause_id]),
        )
        for clause in variant.clauses()
    )
    return clauses, tuple(risks)


def _contract(
    variant: ContractVariant, dataset_dir: Path
) -> tuple[GoldenContract, int]:
    rendered = render_contract(variant.title, variant.clauses())
    clauses, risks = _expectations(variant, rendered.clause_pages)
    contract = GoldenContract(
        schema_version=SCHEMA_VERSION,
        generator_version=GENERATOR_VERSION,
        contract_id=variant.contract_id,
        title=variant.title,
        contract_type=CONTRACT_TYPE,
        jurisdiction=JURISDICTION,
        standard_template_id=STANDARD_TEMPLATE_ID,
        pdf=f"pdfs/{variant.contract_id}.pdf",
        standard_clauses=tuple(
            TemplateClause(
                clause_id=item.clause_id, heading=item.heading, text=item.text
            )
            for item in STANDARD_CLAUSES
        ),
        clauses=clauses,
        risks=risks,
    )
    (dataset_dir / "pdfs" / f"{variant.contract_id}.pdf").write_bytes(rendered.content)
    return contract, rendered.page_count


def _promptfoo_case(
    contract: GoldenContract, variant: ContractVariant
) -> dict[str, object]:
    return {
        "description": f"{contract.contract_id}: {contract.title}",
        "vars": {
            "contract_id": contract.contract_id,
            "contract_type": contract.contract_type,
            "jurisdiction": contract.jurisdiction,
            "expected_file": f"expected/{contract.contract_id}.expected.json",
            "standard_clause_block": clause_block(STANDARD_CLAUSES),
            "contract_clause_block": clause_block(variant.clauses()),
        },
        "metadata": {
            "risk_ids": [risk.risk_id for risk in contract.risks],
            "planted_clause_ids": sorted(
                {clause for risk in contract.risks for clause in risk.clause_ids}
            ),
        },
    }


def _clean_generated(dataset_dir: Path) -> None:
    for folder, suffix in (("pdfs", ".pdf"), ("expected", ".expected.json")):
        for path in (dataset_dir / folder).glob(f"golden-*{suffix}"):
            path.unlink()


def build_dataset(out_dir: Path = DEFAULT_OUT_DIR) -> BuildResult:
    """Build the complete golden set under ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pdfs").mkdir(exist_ok=True)
    (out_dir / "expected").mkdir(exist_ok=True)
    _clean_generated(out_dir)

    contracts: list[GoldenContract] = []
    page_counts: dict[str, int] = {}
    files: list[Path] = []
    for variant in VARIANTS:
        contract, page_count = _contract(variant, out_dir)
        contracts.append(contract)
        page_counts[contract.contract_id] = page_count
        expected_path = out_dir / "expected" / f"{contract.contract_id}.expected.json"
        dump_json(expected_path, contract.to_dict())
        files.extend(
            [
                out_dir / "pdfs" / f"{contract.contract_id}.pdf",
                expected_path,
            ]
        )

    risk_coverage: dict[str, int] = {risk.value: 0 for risk in RiskKind}
    for contract in contracts:
        for risk in contract.risks:
            risk_coverage[risk.risk_id] += 1

    contract_entries: list[dict[str, object]] = []
    dataset_hasher = hashlib.sha256()
    for contract in sorted(contracts, key=lambda item: item.contract_id):
        expected_path = out_dir / "expected" / f"{contract.contract_id}.expected.json"
        expected_sha = _sha256(expected_path.read_bytes())
        dataset_hasher.update(contract.contract_id.encode("utf-8"))
        dataset_hasher.update(expected_sha.encode("ascii"))
        contract_entries.append(
            {
                "contract_id": contract.contract_id,
                "pdf": contract.pdf,
                "expected": f"expected/{contract.contract_id}.expected.json",
                "clause_count": len(contract.clauses),
                "page_count": page_counts[contract.contract_id],
                "risk_ids": [risk.risk_id for risk in contract.risks],
                "sha256_expected": expected_sha,
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "standard_template_id": STANDARD_TEMPLATE_ID,
        "contract_type": CONTRACT_TYPE,
        "jurisdiction": JURISDICTION,
        "contract_count": len(contracts),
        "risk_coverage": risk_coverage,
        "contracts": contract_entries,
        "dataset_sha256": dataset_hasher.hexdigest(),
    }
    dump_json(out_dir / "manifest.json", manifest)
    dump_json(out_dir / "schema.json", GOLDEN_CONTRACT_SCHEMA)
    dump_json(out_dir / "prediction_schema.json", PREDICTION_SCHEMA)

    jsonl_lines = [dump_json_line(contract, out_dir) + "\n" for contract in contracts]
    (out_dir / "golden_set.jsonl").write_text("".join(jsonl_lines), encoding="utf-8")

    dump_json(
        out_dir / "promptfoo_tests.yaml",
        [
            _promptfoo_case(contract, variant)
            for contract, variant in zip(contracts, VARIANTS, strict=True)
        ],
    )

    broken_prompt_output = {
        "description": "Output of the deliberately lenient prompt fixture; must be rejected.",
        "contracts": [
            lenient_prediction(contract).to_dict()
            for contract in sorted(contracts, key=lambda item: item.contract_id)
        ],
    }
    dump_json(out_dir / "fixtures" / "lenient_predictions.json", broken_prompt_output)

    files.extend(
        [
            out_dir / "manifest.json",
            out_dir / "schema.json",
            out_dir / "prediction_schema.json",
            out_dir / "golden_set.jsonl",
            out_dir / "promptfoo_tests.yaml",
            out_dir / "fixtures" / "lenient_predictions.json",
        ]
    )
    return BuildResult(
        dataset_dir=out_dir, contracts=tuple(contracts), files_written=tuple(files)
    )


def dump_json_line(contract: GoldenContract, dataset_dir: Path) -> str:
    """Return one compact golden-set JSONL row."""
    expected = dataset_dir / "expected" / f"{contract.contract_id}.expected.json"
    payload = {
        "contract_id": contract.contract_id,
        "title": contract.title,
        "pdf": contract.pdf,
        "expected": f"expected/{contract.contract_id}.expected.json",
        "clause_count": len(contract.clauses),
        "risk_ids": [risk.risk_id for risk in contract.risks],
        "sha256_expected": _sha256(expected.read_bytes()),
    }
    return json.dumps(payload, ensure_ascii=True)


def _write(text: str) -> None:
    sys.stdout.write(text)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Build the synthetic golden set.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Dataset directory to write (default: evals/datasets).",
    )
    args = parser.parse_args(argv)
    try:
        result = build_dataset(args.out)
    except OSError as error:
        _write(f"Could not build the golden set: {error}\n")
        return 1
    _write(
        f"Built {len(result.contracts)} synthetic contracts in {result.dataset_dir}\n"
    )
    for contract in result.contracts:
        risks = ", ".join(risk.risk_id for risk in contract.risks) or "clean control"
        _write(f"  {contract.contract_id}: {len(contract.clauses)} clauses; {risks}\n")
    _write(f"Wrote {len(result.files_written)} files.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
