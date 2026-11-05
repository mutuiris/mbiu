"""The MB-19 quality gate: planted risks may never pass unflagged.

Run it with ``python -m evals.generator.gate``. The command accepts predictions
from the reference evaluator, a lenient (deliberately broken) evaluator, or a
file produced by the live pipeline. It exits non-zero when any planted clause
risk is labelled ``matches_standard`` without a flag, or when a planted
cross-clause conflict is not surfaced as a contract issue.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from evals.generator.jsonutil import (
    JsonShapeError,
    as_list,
    as_mapping,
    dump_json,
    load_json,
)
from evals.generator.models import (
    ContractPrediction,
    GoldenContract,
    PlantedRisk,
)
from evals.generator.reference_evaluator import evaluate_contract, lenient_prediction
from evals.generator.schema import SchemaValidationError

EVALS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_DIR = EVALS_DIR / "datasets"

REQUIRED_PROMPT_RULES: tuple[str, ...] = (
    "[RULE:PERPETUAL_RIGHTS]",
    "[RULE:EXCLUSIVITY_BEYOND_TERM]",
    "[RULE:MISSING_PAYMENT_DATES]",
    "[RULE:DEDUCTIONS_BEFORE_ROYALTIES]",
    "[RULE:CROSS_CLAUSE_CONFLICTS]",
    "[RULE:NO_UNFLAGGED_MATCH]",
)


@dataclass(frozen=True)
class GateFailure:
    """One reason the quality gate refuses a prediction."""

    contract_id: str
    subject: str
    reason: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {
            "contract_id": self.contract_id,
            "subject": self.subject,
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class GateReport:
    """The gate's verdict for one contract."""

    contract_id: str
    checks: int
    failures: tuple[GateFailure, ...]

    @property
    def passed(self) -> bool:
        """Whether every planted risk in the contract was handled."""
        return not self.failures

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {
            "contract_id": self.contract_id,
            "checks": self.checks,
            "passed": self.passed,
            "failures": [failure.to_dict() for failure in self.failures],
        }


def _clause_risk_failures(
    contract_id: str,
    risk: PlantedRisk,
    prediction: ContractPrediction,
    *,
    strict_outcomes: bool,
) -> list[GateFailure]:
    failures: list[GateFailure] = []
    for clause_id in risk.clause_ids:
        result = prediction.result_for(clause_id)
        subject = f"{risk.risk_id}:{clause_id}"
        if result is None:
            failures.append(
                GateFailure(
                    contract_id=contract_id,
                    subject=subject,
                    reason="missing_clause_result",
                    detail=f"No result was returned for planted risk clause {clause_id}.",
                )
            )
            continue
        if result.comparison == "matches_standard" and not result.risk_flags:
            failures.append(
                GateFailure(
                    contract_id=contract_id,
                    subject=subject,
                    reason="unflagged_match",
                    detail=(
                        f"Planted risk {risk.risk_id} was labelled matches_standard with no "
                        "risk flag."
                    ),
                )
            )
        if strict_outcomes and result.comparison != risk.expected_outcome:
            failures.append(
                GateFailure(
                    contract_id=contract_id,
                    subject=subject,
                    reason="wrong_outcome",
                    detail=(
                        f"Expected {risk.expected_outcome!r} for {risk.risk_id}, "
                        f"got {result.comparison!r}."
                    ),
                )
            )
    return failures


def _conflict_failures(
    contract_id: str,
    risk: PlantedRisk,
    prediction: ContractPrediction,
) -> list[GateFailure]:
    issue = (
        prediction.issue_for(risk.clause_ids, risk.expected_issue_kind)
        if risk.expected_issue_kind is not None
        else None
    )
    if issue is not None:
        return []
    expected = ", ".join(risk.clause_ids)
    return [
        GateFailure(
            contract_id=contract_id,
            subject=risk.risk_id,
            reason="missing_contract_issue",
            detail=(
                f"Planted cross-clause conflict between clauses {expected} was not reported "
                f"as a {risk.expected_issue_kind!r} contract issue."
            ),
        )
    ]


def evaluate_contract_gate(
    expectation: GoldenContract,
    prediction: ContractPrediction,
    *,
    strict_outcomes: bool = False,
) -> GateReport:
    """Apply the 100%-strict gate to one contract."""
    checks = 0
    failures: list[GateFailure] = []
    if prediction.contract_id != expectation.contract_id:
        failures.append(
            GateFailure(
                contract_id=expectation.contract_id,
                subject="contract",
                reason="contract_mismatch",
                detail=(
                    f"Prediction is for {prediction.contract_id!r}, expected "
                    f"{expectation.contract_id!r}."
                ),
            )
        )

    seen: set[str] = set()
    for result in prediction.clause_results:
        if result.clause_id in seen:
            failures.append(
                GateFailure(
                    contract_id=expectation.contract_id,
                    subject=result.clause_id,
                    reason="duplicate_clause_result",
                    detail=f"More than one result was returned for clause {result.clause_id}.",
                )
            )
        seen.add(result.clause_id)

    for risk in expectation.risks:
        checks += 1
        if risk.kind == "cross_clause":
            failures.extend(
                _conflict_failures(expectation.contract_id, risk, prediction)
            )
        else:
            failures.extend(
                _clause_risk_failures(
                    expectation.contract_id,
                    risk,
                    prediction,
                    strict_outcomes=strict_outcomes,
                )
            )

    return GateReport(
        contract_id=expectation.contract_id,
        checks=checks,
        failures=tuple(failures),
    )


def load_expectations(dataset_dir: Path) -> tuple[GoldenContract, ...]:
    """Load and schema-check every expected-outcome sidecar in ``dataset_dir``."""
    paths = sorted((dataset_dir / "expected").glob("*.expected.json"))
    if not paths:
        raise FileNotFoundError(
            f"No expected sidecars under {dataset_dir / 'expected'}"
        )
    return tuple(GoldenContract.from_dict(load_json(path)) for path in paths)


def _prediction_items(payload: object) -> list[tuple[str | None, object]]:
    if isinstance(payload, list):
        return [(None, item) for item in payload]
    mapping = as_mapping(payload, "$")
    if "contracts" in mapping:
        items = as_list(mapping["contracts"], "$.contracts")
        return [(None, item) for item in items]
    return [(key, mapping[key]) for key in sorted(mapping)]


def load_predictions(
    source: str,
    expectations: tuple[GoldenContract, ...],
) -> dict[str, ContractPrediction]:
    """Load predictions from the reference evaluator, the broken fixture, or a file."""
    if source == "reference":
        return {item.contract_id: evaluate_contract(item) for item in expectations}
    if source == "lenient":
        return {item.contract_id: lenient_prediction(item) for item in expectations}

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Predictions not found: {path}")

    by_id: dict[str, ContractPrediction] = {}
    if path.is_dir():
        for expectation in expectations:
            prediction_path = path / f"{expectation.contract_id}.json"
            if prediction_path.exists():
                by_id[expectation.contract_id] = ContractPrediction.from_dict(
                    load_json(prediction_path),
                    contract_id=expectation.contract_id,
                )
        return by_id

    for key, item in _prediction_items(load_json(path)):
        prediction = ContractPrediction.from_dict(item, contract_id=key)
        by_id[prediction.contract_id] = prediction
    return by_id


def prompt_rule_issues(prompt_text: str) -> tuple[str, ...]:
    """Return the required strictness rules a prompt is missing."""
    return tuple(rule for rule in REQUIRED_PROMPT_RULES if rule not in prompt_text)


def run_gate(
    dataset_dir: Path,
    predictions_source: str,
    *,
    strict_outcomes: bool = False,
) -> tuple[GateReport, ...]:
    """Run the gate over every contract in the dataset."""
    expectations = load_expectations(dataset_dir)
    predictions = load_predictions(predictions_source, expectations)
    reports: list[GateReport] = []
    for expectation in expectations:
        prediction = predictions.get(expectation.contract_id)
        if prediction is None:
            reports.append(
                GateReport(
                    contract_id=expectation.contract_id,
                    checks=len(expectation.risks),
                    failures=(
                        GateFailure(
                            contract_id=expectation.contract_id,
                            subject="contract",
                            reason="missing_prediction",
                            detail="No evaluation was returned for this contract.",
                        ),
                    ),
                )
            )
            continue
        reports.append(
            evaluate_contract_gate(
                expectation,
                prediction,
                strict_outcomes=strict_outcomes,
            )
        )
    return tuple(reports)


def _write(text: str) -> None:
    sys.stdout.write(text)


def _report_text(reports: Sequence[GateReport]) -> str:
    lines: list[str] = []
    total_failures = sum(len(report.failures) for report in reports)
    lines.append(
        f"Quality gate: {len(reports)} contracts, "
        f"{sum(report.checks for report in reports)} planted risks, "
        f"{total_failures} failure(s).\n"
    )
    for report in reports:
        status = "PASS" if report.passed else "FAIL"
        lines.append(
            f"  {status} {report.contract_id} ({report.checks} risks checked)\n"
        )
        for failure in report.failures:
            lines.append(
                f"    - {failure.reason} [{failure.subject}] {failure.detail}\n"
            )
    return "".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="MB-19 golden-set quality gate.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Directory containing expected/ and manifest.json.",
    )
    parser.add_argument(
        "--predictions",
        default="reference",
        help="'reference', 'lenient', a predictions directory, or a JSON file.",
    )
    parser.add_argument(
        "--strict-outcomes",
        action="store_true",
        help="Also require the exact expected comparison for each planted clause risk.",
    )
    parser.add_argument(
        "--check-prompt",
        type=Path,
        help="Only check that a prompt contains every required strictness rule.",
    )
    parser.add_argument(
        "--expect-fail",
        action="store_true",
        help="Succeed only when the gate rejects the predictions (used to test the gate).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Write a machine-readable report to this path.",
    )
    args = parser.parse_args(argv)

    try:
        if args.check_prompt is not None:
            issues = prompt_rule_issues(args.check_prompt.read_text(encoding="utf-8"))
            if issues:
                _write("Prompt is missing required strictness rules:\n")
                for issue in issues:
                    _write(f"  - {issue}\n")
                return 1
            _write(
                f"Prompt contains all {len(REQUIRED_PROMPT_RULES)} required rules.\n"
            )
            return 0

        reports = run_gate(
            args.dataset,
            args.predictions,
            strict_outcomes=args.strict_outcomes,
        )
    except (
        FileNotFoundError,
        JsonShapeError,
        SchemaValidationError,
        ValueError,
    ) as error:
        _write(f"Quality gate error: {error}\n")
        return 1

    _write(_report_text(reports))
    passed = all(report.passed for report in reports)
    if args.json_out is not None:
        dump_json(
            args.json_out,
            {
                "schema_version": 1,
                "strict_outcomes": args.strict_outcomes,
                "predictions": args.predictions,
                "passed": passed,
                "contracts": [report.to_dict() for report in reports],
            },
        )
    if args.expect_fail:
        if passed:
            _write("ERROR: the gate unexpectedly accepted these predictions.\n")
            return 1
        _write("Gate correctly rejected the predictions.\n")
        return 0
    if not passed:
        _write("ERROR: the quality gate blocked this evaluation.\n")
        return 1
    _write("Quality gate passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
