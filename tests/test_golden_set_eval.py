"""Hermetic tests for the MB-19 golden set and quality gate.

No test in this module reaches the network. The Gemini path is exercised with a
fake HTTP response so standard ``pytest`` runs stay fast and offline.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import httpx
import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.generator import GENERATOR_VERSION, SCHEMA_VERSION
from evals.generator import assertion as assertion_module
from evals.generator import provider as provider_module
from evals.generator.assertion import get_assert
from evals.generator.build import BuildResult, build_dataset
from evals.generator.build import main as build_main
from evals.generator.gate import (
    evaluate_contract_gate,
    prompt_rule_issues,
    run_gate,
)
from evals.generator.gate import (
    main as gate_main,
)
from evals.generator.jsonutil import as_mapping, load_json
from evals.generator.models import ContractPrediction, GoldenContract
from evals.generator.provider import call_api
from evals.generator.reference_evaluator import evaluate_contract, lenient_prediction
from evals.generator.risks import RISK_DEFINITIONS_BY_ID, RiskKind
from evals.generator.schema import (
    GOLDEN_CONTRACT_SCHEMA,
    SchemaValidationError,
    validate,
)

EXPECTED_RISK_COVERAGE = {
    "perpetual_rights": 2,
    "exclusivity_beyond_term": 2,
    "missing_payment_dates": 2,
    "deductions_before_royalties": 2,
    "cross_clause_conflict": 2,
}
RISK_CONTRACT_IDS = {
    "mb19-perpetual-rights",
    "mb19-exclusivity-beyond-term",
    "mb19-missing-payment-dates",
    "mb19-deductions-before-royalties",
    "mb19-cross-clause-conflict",
    "mb19-combined-risks",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> BuildResult:
    """Build one fresh golden set for the whole module."""
    return build_dataset(tmp_path_factory.mktemp("golden-set"))


def _expectation(built: BuildResult, contract_id: str) -> GoldenContract:
    path = built.dataset_dir / "expected" / f"{contract_id}.expected.json"
    return GoldenContract.from_dict(load_json(path))


def _predictions(built: BuildResult) -> dict[str, ContractPrediction]:
    return {
        contract.contract_id: evaluate_contract(contract)
        for contract in built.contracts
    }


def _normalise(text: str) -> str:
    return " ".join(text.split())


def test_builds_contracts_sidecars_and_promptfoo_cases(built: BuildResult) -> None:
    contract_ids = {contract.contract_id for contract in built.contracts}
    assert contract_ids == {
        "mb19-clean-control",
        "mb19-perpetual-rights",
        "mb19-exclusivity-beyond-term",
        "mb19-missing-payment-dates",
        "mb19-deductions-before-royalties",
        "mb19-cross-clause-conflict",
        "mb19-combined-risks",
    }
    assert len(built.contracts) == 7

    manifest = as_mapping(load_json(built.dataset_dir / "manifest.json"), "manifest")
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["generator_version"] == GENERATOR_VERSION
    assert manifest["contract_count"] == 7
    assert manifest["risk_coverage"] == EXPECTED_RISK_COVERAGE

    for contract in built.contracts:
        assert (built.dataset_dir / contract.pdf).is_file()
        sidecar = (
            built.dataset_dir / "expected" / f"{contract.contract_id}.expected.json"
        )
        assert sidecar.is_file()
        assert len(contract.clauses) == 13
        assert len(contract.standard_clauses) == 13

    cases = json.loads((built.dataset_dir / "promptfoo_tests.yaml").read_text("utf-8"))
    assert len(cases) == 7
    for case in cases:
        assert (built.dataset_dir / case["vars"]["expected_file"]).is_file()
        assert case["vars"]["contract_clause_block"]
        assert case["vars"]["standard_clause_block"]


def test_every_sidecar_validates_against_the_json_schema(built: BuildResult) -> None:
    schema = as_mapping(load_json(built.dataset_dir / "schema.json"), "schema")
    assert schema == GOLDEN_CONTRACT_SCHEMA

    for path in sorted((built.dataset_dir / "expected").glob("*.expected.json")):
        payload = load_json(path)
        validate(payload, schema)
        contract = GoldenContract.from_dict(payload)
        assert contract.schema_version == SCHEMA_VERSION
        assert contract.generator_version == GENERATOR_VERSION


def test_clause_and_risk_ground_truth_is_consistent(built: BuildResult) -> None:
    manifest = as_mapping(load_json(built.dataset_dir / "manifest.json"), "manifest")
    page_counts = _manifest_page_counts(manifest)
    for contract in built.contracts:
        clause_ids = [clause.clause_id for clause in contract.clauses]
        assert len(clause_ids) == len(set(clause_ids))
        for clause in contract.clauses:
            assert clause.text
            assert clause.pages
            assert all(
                1 <= page <= page_counts[contract.contract_id] for page in clause.pages
            )

        for risk in contract.risks:
            assert risk.pages
            assert all(
                1 <= page <= page_counts[contract.contract_id] for page in risk.pages
            )
            risk_clause_pages: set[int] = set()
            for clause_id in risk.clause_ids:
                risk_clause = contract.clause(clause_id)
                assert risk_clause is not None
                risk_clause_pages.update(risk_clause.pages)
            assert set(risk.pages) == risk_clause_pages


def _manifest_contracts(manifest: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw = manifest["contracts"]
    assert isinstance(raw, list)
    return [as_mapping(item, "manifest.contracts[]") for item in raw]


def _manifest_page_counts(manifest: Mapping[str, object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in _manifest_contracts(manifest):
        contract_id = item["contract_id"]
        page_count = item["page_count"]
        assert isinstance(contract_id, str)
        assert isinstance(page_count, int) and not isinstance(page_count, bool)
        counts[contract_id] = page_count
    return counts


def test_planted_risks_are_present_in_the_pdf_text(built: BuildResult) -> None:
    for contract in built.contracts:
        document = pymupdf.open(str(built.dataset_dir / contract.pdf))
        try:
            text = _normalise(
                "\n".join(
                    document[index].get_text() for index in range(document.page_count)
                )
            )
            assert len(document) == _manifest_page_count(built, contract.contract_id)
        finally:
            document.close()
        for risk in contract.risks:
            marker = RISK_DEFINITIONS_BY_ID[RiskKind(risk.risk_id)].marker
            assert marker in _normalise(text)
            expected = _expectation(built, contract.contract_id)
            for clause_id in risk.clause_ids:
                clause = expected.clause(clause_id)
                assert clause is not None
                assert _normalise(clause.text) in text


def _manifest_page_count(built: BuildResult, contract_id: str) -> int:
    manifest = as_mapping(load_json(built.dataset_dir / "manifest.json"), "manifest")
    return _manifest_page_counts(manifest)[contract_id]


def test_reference_evaluator_passes_the_gate_with_strict_outcomes(
    built: BuildResult,
) -> None:
    reports = run_gate(built.dataset_dir, "reference", strict_outcomes=True)
    assert len(reports) == 7
    assert all(report.passed for report in reports)
    assert sum(report.checks for report in reports) == 10


def test_lenient_predictions_fail_every_planted_risk(built: BuildResult) -> None:
    reports = {
        report.contract_id: report for report in run_gate(built.dataset_dir, "lenient")
    }
    assert reports["mb19-clean-control"].passed
    failures = [failure for report in reports.values() for failure in report.failures]
    assert len(failures) == 10
    reasons = {failure.reason for failure in failures}
    assert reasons == {"unflagged_match", "missing_contract_issue"}
    assert {
        report.contract_id for report in reports.values() if not report.passed
    } == RISK_CONTRACT_IDS


def test_gate_cli_blocks_lenient_fixture_and_expect_fail(
    built: BuildResult, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = str(built.dataset_dir)
    fixture = str(built.dataset_dir / "fixtures" / "lenient_predictions.json")

    assert gate_main(["--dataset", dataset, "--predictions", "lenient"]) == 1
    capsys.readouterr()
    assert gate_main(["--dataset", dataset, "--predictions", fixture]) == 1
    capsys.readouterr()
    assert (
        gate_main(["--dataset", dataset, "--predictions", fixture, "--expect-fail"])
        == 0
    )
    capsys.readouterr()
    assert gate_main(["--dataset", dataset, "--predictions", "reference"]) == 0
    capsys.readouterr()


def test_provider_reference_mode_never_calls_the_network(
    built: BuildResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _explode(*args: object, **kwargs: object) -> httpx.Response:
        del args, kwargs
        raise AssertionError("reference mode must not open the network")

    monkeypatch.setattr(provider_module, "DATASETS_DIR", built.dataset_dir)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(httpx.Client, "post", _explode)

    contract = _expectation(built, "mb19-combined-risks")
    result = call_api(
        "rendered prompt",
        {"config": {"mode": "reference"}},
        {"vars": {"expected_file": f"expected/{contract.contract_id}.expected.json"}},
    )
    prediction = ContractPrediction.from_dict(
        json.loads(str(result["output"])), contract_id=contract.contract_id
    )
    assert evaluate_contract_gate(contract, prediction).passed
    metadata = as_mapping(result["metadata"], "metadata")
    assert metadata["mode"] == "reference"


def test_provider_gemini_mode_uses_mocked_api(
    built: BuildResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = _expectation(built, "mb19-perpetual-rights")
    reference = evaluate_contract(contract)
    payload = json.dumps(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(reference.to_dict())}],
                    }
                }
            ]
        }
    )

    def _respond(self: httpx.Client, url: str, **kwargs: object) -> httpx.Response:
        del self, kwargs
        request = httpx.Request("POST", url)
        return httpx.Response(200, content=payload, request=request)

    monkeypatch.setattr(provider_module, "DATASETS_DIR", built.dataset_dir)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(httpx.Client, "post", _respond)

    result = call_api(
        "rendered prompt",
        {"config": {"mode": "gemini", "model": "gemini-test"}},
        {"vars": {"expected_file": f"expected/{contract.contract_id}.expected.json"}},
    )
    prediction = ContractPrediction.from_dict(
        json.loads(str(result["output"])), contract_id=contract.contract_id
    )
    assert evaluate_contract_gate(contract, prediction).passed
    metadata = as_mapping(result["metadata"], "metadata")
    assert metadata["mode"] == "gemini"
    assert metadata["model"] == "gemini-test"


def test_provider_lenient_mode_is_rejected_by_the_gate(
    built: BuildResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(provider_module, "DATASETS_DIR", built.dataset_dir)
    contract = _expectation(built, "mb19-missing-payment-dates")
    result = call_api(
        "rendered prompt",
        {"config": {"mode": "lenient"}},
        {"vars": {"expected_file": f"expected/{contract.contract_id}.expected.json"}},
    )
    prediction = ContractPrediction.from_dict(
        json.loads(str(result["output"])), contract_id=contract.contract_id
    )
    report = evaluate_contract_gate(contract, prediction)
    assert not report.passed


def test_assertion_accepts_reference_and_rejects_lenient(
    built: BuildResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assertion_module, "DATASETS_DIR", built.dataset_dir)
    contract = _expectation(built, "mb19-cross-clause-conflict")
    perpetual = _expectation(built, "mb19-perpetual-rights")
    perpetual_prediction = evaluate_contract(perpetual)
    context = {
        "vars": {"expected_file": f"expected/{contract.contract_id}.expected.json"}
    }

    reference_result = get_assert(
        json.dumps(evaluate_contract(contract).to_dict()), context
    )
    assert reference_result["pass"] is True

    lenient_result = get_assert(
        json.dumps(lenient_prediction(contract).to_dict()), context
    )
    assert lenient_result["pass"] is False
    assert "missing_contract_issue" in str(lenient_result["reason"])

    misclassified = replace(
        perpetual_prediction,
        clause_results=tuple(
            replace(result, comparison="better_for_you")
            if result.clause_id == "3.1"
            else result
            for result in perpetual_prediction.clause_results
        ),
    )
    perpetual_context = {
        "vars": {"expected_file": f"expected/{perpetual.contract_id}.expected.json"}
    }
    misclassified_result = get_assert(
        json.dumps(misclassified.to_dict()), perpetual_context
    )
    assert misclassified_result["pass"] is False
    assert "wrong_outcome" in str(misclassified_result["reason"])

    error_result = get_assert("not json", context)
    assert error_result["pass"] is False
    assert "gate error" in str(error_result["reason"])


def test_gate_requires_a_conflict_issue_even_when_both_clauses_are_flagged(
    built: BuildResult,
) -> None:
    contract = _expectation(built, "mb19-cross-clause-conflict")
    prediction = replace(evaluate_contract(contract), contract_issues=())
    report = evaluate_contract_gate(contract, prediction)
    assert not report.passed
    assert [failure.reason for failure in report.failures] == ["missing_contract_issue"]


def test_gate_requires_a_result_for_every_planted_clause(built: BuildResult) -> None:
    contract = _expectation(built, "mb19-deductions-before-royalties")
    prediction = evaluate_contract(contract)
    prediction = replace(
        prediction,
        clause_results=tuple(
            result for result in prediction.clause_results if result.clause_id != "4.1"
        ),
    )
    report = evaluate_contract_gate(contract, prediction)
    assert not report.passed
    assert [failure.reason for failure in report.failures] == ["missing_clause_result"]


def test_matches_standard_with_an_explicit_risk_flag_is_flagged(
    built: BuildResult,
) -> None:
    contract = _expectation(built, "mb19-perpetual-rights")
    prediction = evaluate_contract(contract)
    prediction = replace(
        prediction,
        clause_results=tuple(
            replace(
                result, comparison="matches_standard", risk_flags=("perpetual_rights",)
            )
            if result.clause_id == "3.1"
            else result
            for result in prediction.clause_results
        ),
    )
    assert evaluate_contract_gate(contract, prediction).passed


def test_clean_control_passes_with_standard_predictions(built: BuildResult) -> None:
    contract = _expectation(built, "mb19-clean-control")
    report = evaluate_contract_gate(contract, lenient_prediction(contract))
    assert report.passed
    assert report.checks == 0


def test_good_prompt_has_rules_and_broken_prompt_does_not() -> None:
    prompt_dir = Path(__file__).resolve().parents[1] / "evals" / "generator" / "prompts"
    good = (prompt_dir / "mbiu_clause_eval.txt").read_text("utf-8")
    broken = (prompt_dir / "lenient_clause_eval.txt").read_text("utf-8")
    assert prompt_rule_issues(good) == ()
    assert len(prompt_rule_issues(broken)) == 6
    assert gate_main(["--check-prompt", str(prompt_dir / "mbiu_clause_eval.txt")]) == 0
    assert (
        gate_main(["--check-prompt", str(prompt_dir / "lenient_clause_eval.txt")]) == 1
    )


def test_rebuild_is_deterministic_for_sidecars_and_manifest(
    built: BuildResult, tmp_path: Path
) -> None:
    rebuilt = build_dataset(tmp_path / "rebuilt")
    assert rebuilt.contracts == built.contracts
    for contract in built.contracts:
        name = f"{contract.contract_id}.expected.json"
        assert (rebuilt.dataset_dir / "expected" / name).read_bytes() == (
            built.dataset_dir / "expected" / name
        ).read_bytes()
    assert (rebuilt.dataset_dir / "manifest.json").read_bytes() == (
        built.dataset_dir / "manifest.json"
    ).read_bytes()
    assert (rebuilt.dataset_dir / "golden_set.jsonl").read_bytes() == (
        built.dataset_dir / "golden_set.jsonl"
    ).read_bytes()


def test_prediction_schema_rejects_unknown_comparison() -> None:
    with pytest.raises(SchemaValidationError):
        ContractPrediction.from_dict(
            {
                "contract_id": "mb19-clean-control",
                "clause_results": [
                    {
                        "clause_id": "1.1",
                        "status": "evaluated",
                        "comparison": "probably_fine",
                        "risk_flags": [],
                    }
                ],
                "contract_issues": [],
            }
        )


def test_build_cli(tmp_path: Path) -> None:
    assert build_main(["--out", str(tmp_path / "from-cli")]) == 0
    assert (tmp_path / "from-cli" / "manifest.json").is_file()
