"""Promptfoo Python assertion that applies the quality gate.

The assertion loads the ground-truth sidecar named in the test's
``expected_file`` variable, so it does not trust the provider's own verdict.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.generator.gate import evaluate_contract_gate
from evals.generator.jsonutil import as_mapping, as_str, load_json
from evals.generator.models import ContractPrediction, GoldenContract

EVALS_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = EVALS_DIR / "datasets"


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected an object")
    return as_mapping(value, path)


def get_assert(output: object, context: object) -> dict[str, object]:
    """Return a Promptfoo grading result for one contract."""
    try:
        context_data = _mapping(context, "context")
        variables = _mapping(context_data.get("vars", {}), "context.vars")
        expected_file = as_str(variables.get("expected_file"), "vars.expected_file")
        contract = GoldenContract.from_dict(load_json(DATASETS_DIR / expected_file))

        if isinstance(output, dict):
            payload: object = output
        elif isinstance(output, str):
            payload = json.loads(output)
        else:
            raise TypeError("output must be JSON text or an object")

        prediction = ContractPrediction.from_dict(
            payload,
            contract_id=contract.contract_id,
        )
        report = evaluate_contract_gate(contract, prediction, strict_outcomes=True)
    except (OSError, ValueError, TypeError) as error:
        return {
            "pass": False,
            "score": 0.0,
            "reason": f"golden-set gate error: {error}",
        }

    if report.passed:
        return {
            "pass": True,
            "score": 1.0,
            "reason": f"{contract.contract_id}: all {report.checks} planted risks passed.",
        }
    details = "; ".join(
        f"{failure.reason} [{failure.subject}]: {failure.detail}"
        for failure in report.failures
    )
    return {
        "pass": False,
        "score": 0.0,
        "reason": f"{contract.contract_id}: gate refused the result. {details}",
    }
