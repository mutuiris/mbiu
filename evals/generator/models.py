"""Typed golden-set documents and model predictions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from evals.generator.jsonutil import (
    as_int,
    as_int_list,
    as_list,
    as_mapping,
    as_optional_str,
    as_str,
    as_str_list,
)
from evals.generator.schema import (
    GOLDEN_CONTRACT_SCHEMA,
    PREDICTION_SCHEMA,
    validate,
)


@dataclass(frozen=True)
class TemplateClause:
    """One clause from the reviewed standard template."""

    clause_id: str
    heading: str
    text: str

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {"clause_id": self.clause_id, "heading": self.heading, "text": self.text}

    @classmethod
    def from_dict(cls, value: object, *, path: str = "$") -> TemplateClause:
        """Parse and validate one template clause."""
        data = as_mapping(value, path)
        return cls(
            clause_id=as_str(data.get("clause_id"), f"{path}.clause_id"),
            heading=as_str(data.get("heading"), f"{path}.heading"),
            text=as_str(data.get("text"), f"{path}.text"),
        )


@dataclass(frozen=True)
class ClauseExpectation:
    """The known-by-construction outcome for one contract clause."""

    clause_id: str
    heading: str
    pages: tuple[int, ...]
    text: str
    expected_outcome: str
    planted_risk_ids: tuple[str, ...]
    conflict_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {
            "clause_id": self.clause_id,
            "heading": self.heading,
            "pages": list(self.pages),
            "text": self.text,
            "expected_outcome": self.expected_outcome,
            "planted_risk_ids": list(self.planted_risk_ids),
            "conflict_ids": list(self.conflict_ids),
        }

    @classmethod
    def from_dict(cls, value: object, *, path: str = "$") -> ClauseExpectation:
        """Parse and validate one clause expectation."""
        data = as_mapping(value, path)
        return cls(
            clause_id=as_str(data.get("clause_id"), f"{path}.clause_id"),
            heading=as_str(data.get("heading"), f"{path}.heading"),
            pages=as_int_list(data.get("pages"), f"{path}.pages"),
            text=as_str(data.get("text"), f"{path}.text"),
            expected_outcome=as_str(
                data.get("expected_outcome"), f"{path}.expected_outcome"
            ),
            planted_risk_ids=as_str_list(
                data.get("planted_risk_ids"), f"{path}.planted_risk_ids"
            ),
            conflict_ids=as_str_list(data.get("conflict_ids"), f"{path}.conflict_ids"),
        )


@dataclass(frozen=True)
class PlantedRisk:
    """A risk inserted by construction, with the clause(s) it affects."""

    risk_id: str
    kind: str
    description: str
    clause_ids: tuple[str, ...]
    pages: tuple[int, ...]
    expected_outcome: str | None
    expected_issue_kind: str | None

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {
            "risk_id": self.risk_id,
            "kind": self.kind,
            "description": self.description,
            "clause_ids": list(self.clause_ids),
            "pages": list(self.pages),
            "expected_outcome": self.expected_outcome,
            "expected_issue_kind": self.expected_issue_kind,
        }

    @classmethod
    def from_dict(cls, value: object, *, path: str = "$") -> PlantedRisk:
        """Parse and validate one planted risk."""
        data = as_mapping(value, path)
        return cls(
            risk_id=as_str(data.get("risk_id"), f"{path}.risk_id"),
            kind=as_str(data.get("kind"), f"{path}.kind"),
            description=as_str(data.get("description"), f"{path}.description"),
            clause_ids=as_str_list(data.get("clause_ids"), f"{path}.clause_ids"),
            pages=as_int_list(data.get("pages"), f"{path}.pages"),
            expected_outcome=as_optional_str(
                data.get("expected_outcome"), f"{path}.expected_outcome"
            ),
            expected_issue_kind=as_optional_str(
                data.get("expected_issue_kind"), f"{path}.expected_issue_kind"
            ),
        )


@dataclass(frozen=True)
class GoldenContract:
    """A generated synthetic contract and everything the gate knows about it."""

    schema_version: int
    generator_version: str
    contract_id: str
    title: str
    contract_type: str
    jurisdiction: str
    standard_template_id: str
    pdf: str
    standard_clauses: tuple[TemplateClause, ...]
    clauses: tuple[ClauseExpectation, ...]
    risks: tuple[PlantedRisk, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the JSON sidecar representation."""
        return {
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "contract_id": self.contract_id,
            "title": self.title,
            "contract_type": self.contract_type,
            "jurisdiction": self.jurisdiction,
            "standard_template_id": self.standard_template_id,
            "pdf": self.pdf,
            "standard_clauses": [clause.to_dict() for clause in self.standard_clauses],
            "clauses": [clause.to_dict() for clause in self.clauses],
            "risks": [risk.to_dict() for risk in self.risks],
        }

    @classmethod
    def from_dict(cls, value: object, *, path: str = "$") -> GoldenContract:
        """Parse a sidecar and enforce the golden-set JSON Schema."""
        data = as_mapping(value, path)
        validate(data, GOLDEN_CONTRACT_SCHEMA, path=path)
        return cls(
            schema_version=as_int(data.get("schema_version"), f"{path}.schema_version"),
            generator_version=as_str(
                data.get("generator_version"), f"{path}.generator_version"
            ),
            contract_id=as_str(data.get("contract_id"), f"{path}.contract_id"),
            title=as_str(data.get("title"), f"{path}.title"),
            contract_type=as_str(data.get("contract_type"), f"{path}.contract_type"),
            jurisdiction=as_str(data.get("jurisdiction"), f"{path}.jurisdiction"),
            standard_template_id=as_str(
                data.get("standard_template_id"), f"{path}.standard_template_id"
            ),
            pdf=as_str(data.get("pdf"), f"{path}.pdf"),
            standard_clauses=tuple(
                TemplateClause.from_dict(item, path=f"{path}.standard_clauses[{index}]")
                for index, item in enumerate(
                    as_list(data.get("standard_clauses"), f"{path}.standard_clauses")
                )
            ),
            clauses=tuple(
                ClauseExpectation.from_dict(item, path=f"{path}.clauses[{index}]")
                for index, item in enumerate(
                    as_list(data.get("clauses"), f"{path}.clauses")
                )
            ),
            risks=tuple(
                PlantedRisk.from_dict(item, path=f"{path}.risks[{index}]")
                for index, item in enumerate(
                    as_list(data.get("risks"), f"{path}.risks")
                )
            ),
        )

    def clause(self, clause_id: str) -> ClauseExpectation | None:
        """Return one clause expectation by ID, if present."""
        for clause in self.clauses:
            if clause.clause_id == clause_id:
                return clause
        return None


@dataclass(frozen=True)
class ClausePrediction:
    """What an evaluator said about one clause."""

    clause_id: str
    status: str
    comparison: str
    risk_flags: tuple[str, ...]
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {
            "clause_id": self.clause_id,
            "status": self.status,
            "comparison": self.comparison,
            "risk_flags": list(self.risk_flags),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, value: object, *, path: str = "$") -> ClausePrediction:
        """Parse one clause prediction."""
        data = as_mapping(value, path)
        return cls(
            clause_id=as_str(data.get("clause_id"), f"{path}.clause_id"),
            status=as_str(data.get("status", "evaluated"), f"{path}.status"),
            comparison=as_str(data.get("comparison"), f"{path}.comparison"),
            risk_flags=as_str_list(data.get("risk_flags", []), f"{path}.risk_flags"),
            note=as_optional_str(data.get("note"), f"{path}.note"),
        )


@dataclass(frozen=True)
class ContractIssuePrediction:
    """A contract-wide issue found by an evaluator."""

    issue_id: str
    kind: str
    clause_ids: tuple[str, ...]
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {
            "issue_id": self.issue_id,
            "kind": self.kind,
            "clause_ids": list(self.clause_ids),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, value: object, *, path: str = "$") -> ContractIssuePrediction:
        """Parse one contract issue."""
        data = as_mapping(value, path)
        return cls(
            issue_id=as_str(data.get("issue_id"), f"{path}.issue_id"),
            kind=as_str(data.get("kind"), f"{path}.kind"),
            clause_ids=as_str_list(data.get("clause_ids"), f"{path}.clause_ids"),
            note=as_optional_str(data.get("note"), f"{path}.note"),
        )


@dataclass(frozen=True)
class ContractPrediction:
    """The evaluator output the quality gate judges for one contract."""

    contract_id: str
    clause_results: tuple[ClausePrediction, ...]
    contract_issues: tuple[ContractIssuePrediction, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the JSON representation."""
        return {
            "contract_id": self.contract_id,
            "clause_results": [result.to_dict() for result in self.clause_results],
            "contract_issues": [issue.to_dict() for issue in self.contract_issues],
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        contract_id: str | None = None,
        path: str = "$",
    ) -> ContractPrediction:
        """Parse a prediction, accepting the prompt's ``clauses`` alias."""
        data = dict(as_mapping(value, path))
        if "clause_results" not in data and "clauses" in data:
            data["clause_results"] = data.pop("clauses")
        if "contract_id" not in data and contract_id is not None:
            data["contract_id"] = contract_id
        if "contract_issues" not in data:
            data["contract_issues"] = []
        validate(data, PREDICTION_SCHEMA, path=path)
        parsed_id = as_str(data.get("contract_id"), f"{path}.contract_id")
        if contract_id is not None and parsed_id != contract_id:
            raise ValueError(
                f"{path}.contract_id: expected {contract_id!r}, got {parsed_id!r}"
            )
        return cls(
            contract_id=parsed_id,
            clause_results=tuple(
                ClausePrediction.from_dict(item, path=f"{path}.clause_results[{index}]")
                for index, item in enumerate(
                    as_list(data.get("clause_results"), f"{path}.clause_results")
                )
            ),
            contract_issues=tuple(
                ContractIssuePrediction.from_dict(
                    item, path=f"{path}.contract_issues[{index}]"
                )
                for index, item in enumerate(
                    as_list(data.get("contract_issues"), f"{path}.contract_issues")
                )
            ),
        )

    def result_for(self, clause_id: str) -> ClausePrediction | None:
        """Return the prediction for one clause, if present."""
        for result in self.clause_results:
            if result.clause_id == clause_id:
                return result
        return None

    def issue_for(
        self, clause_ids: tuple[str, ...], kind: str
    ) -> ContractIssuePrediction | None:
        """Return an issue whose kind and clause set match the planted conflict."""
        expected = set(clause_ids)
        for issue in self.contract_issues:
            if issue.kind == kind and set(issue.clause_ids) == expected:
                return issue
        return None


def prediction_from_mapping(
    value: Mapping[str, object], *, contract_id: str | None = None
) -> ContractPrediction:
    """Build a prediction from an already-parsed mapping."""
    return ContractPrediction.from_dict(value, contract_id=contract_id)
