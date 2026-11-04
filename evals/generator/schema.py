"""JSON Schema documents for golden-set sidecars and a focused schema validator.

The validator covers the keywords used by the two schemas below. Keeping it in
the standard library means the Promptfoo Python assertions can validate results
without depending on the Django or Pydantic environment.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from evals.generator.jsonutil import as_list, as_mapping, as_str, as_str_list

SCHEMA_VERSION = 1

OUTCOMES: tuple[str, ...] = (
    "matches_standard",
    "better_for_you",
    "worse_for_you",
    "not_in_standard",
    "missing_from_contract",
    "cannot_compare",
)

CLAUSE_STATUSES: tuple[str, ...] = (
    "evaluated",
    "cannot_compare",
    "evaluation_failed",
    "not_checked",
)

RISK_IDS: tuple[str, ...] = (
    "perpetual_rights",
    "exclusivity_beyond_term",
    "missing_payment_dates",
    "deductions_before_royalties",
    "cross_clause_conflict",
)

CLAUSE_ID_PATTERN = r"^[0-9]+(?:\.[0-9]+)*(?:\([a-z0-9]+\))?$"


class SchemaValidationError(ValueError):
    """Raised when a document does not satisfy its JSON Schema."""

    def __init__(self, path: str, message: str) -> None:
        """Store the failing location alongside a human-readable message."""
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


GOLDEN_CONTRACT_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Mbiu synthetic golden-set contract expectation",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "generator_version",
        "contract_id",
        "title",
        "contract_type",
        "jurisdiction",
        "standard_template_id",
        "pdf",
        "standard_clauses",
        "clauses",
        "risks",
    ],
    "properties": {
        "schema_version": {"type": "integer", "const": SCHEMA_VERSION},
        "generator_version": {"type": "string", "minLength": 1},
        "contract_id": {"type": "string", "pattern": r"^mb19-[a-z0-9-]+$"},
        "title": {"type": "string", "minLength": 1},
        "contract_type": {"type": "string", "const": "recording"},
        "jurisdiction": {"type": "string", "const": "Kenya"},
        "standard_template_id": {"type": "string", "minLength": 1},
        "pdf": {"type": "string", "pattern": r"^pdfs/.+\.pdf$"},
        "standard_clauses": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/$defs/template_clause"},
        },
        "clauses": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/$defs/clause"},
        },
        "risks": {
            "type": "array",
            "items": {"$ref": "#/$defs/risk"},
        },
    },
    "$defs": {
        "template_clause": {
            "type": "object",
            "additionalProperties": False,
            "required": ["clause_id", "heading", "text"],
            "properties": {
                "clause_id": {"type": "string", "pattern": CLAUSE_ID_PATTERN},
                "heading": {"type": "string"},
                "text": {"type": "string", "minLength": 1},
            },
        },
        "clause": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "clause_id",
                "heading",
                "pages",
                "text",
                "expected_outcome",
                "planted_risk_ids",
                "conflict_ids",
            ],
            "properties": {
                "clause_id": {"type": "string", "pattern": CLAUSE_ID_PATTERN},
                "heading": {"type": "string"},
                "pages": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "integer", "minimum": 1},
                },
                "text": {"type": "string", "minLength": 1},
                "expected_outcome": {"type": "string", "enum": list(OUTCOMES)},
                "planted_risk_ids": {"type": "array", "items": {"type": "string"}},
                "conflict_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
        "risk": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "risk_id",
                "kind",
                "description",
                "clause_ids",
                "pages",
                "expected_outcome",
                "expected_issue_kind",
            ],
            "properties": {
                "risk_id": {"type": "string", "enum": list(RISK_IDS)},
                "kind": {"type": "string", "enum": ["clause", "cross_clause"]},
                "description": {"type": "string", "minLength": 1},
                "clause_ids": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "pages": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "integer", "minimum": 1},
                },
                "expected_outcome": {
                    "type": ["string", "null"],
                    "enum": [*OUTCOMES, None],
                },
                "expected_issue_kind": {"type": ["string", "null"]},
            },
        },
    },
}


PREDICTION_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Mbiu golden-set evaluation prediction",
    "type": "object",
    "additionalProperties": True,
    "required": ["contract_id", "clause_results", "contract_issues"],
    "properties": {
        "contract_id": {"type": "string", "minLength": 1},
        "clause_results": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/$defs/clause_result"},
        },
        "contract_issues": {
            "type": "array",
            "items": {"$ref": "#/$defs/contract_issue"},
        },
    },
    "$defs": {
        "clause_result": {
            "type": "object",
            "additionalProperties": True,
            "required": ["clause_id", "status", "comparison", "risk_flags"],
            "properties": {
                "clause_id": {"type": "string", "pattern": CLAUSE_ID_PATTERN},
                "status": {"type": "string", "enum": list(CLAUSE_STATUSES)},
                "comparison": {"type": "string", "enum": list(OUTCOMES)},
                "risk_flags": {"type": "array", "items": {"type": "string"}},
                "note": {"type": ["string", "null"]},
            },
        },
        "contract_issue": {
            "type": "object",
            "additionalProperties": True,
            "required": ["issue_id", "kind", "clause_ids"],
            "properties": {
                "issue_id": {"type": "string", "minLength": 1},
                "kind": {"type": "string", "minLength": 1},
                "clause_ids": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "note": {"type": ["string", "null"]},
            },
        },
    },
}


def validate(
    instance: object, schema: Mapping[str, object], *, path: str = "$"
) -> None:
    """Validate ``instance`` against ``schema`` or raise ``SchemaValidationError``."""
    _validate(instance, schema, schema, path)


def _validate(
    instance: object,
    schema: Mapping[str, object],
    root: Mapping[str, object],
    path: str,
) -> None:
    reference = schema.get("$ref")
    if reference is not None:
        target = _resolve_reference(as_str(reference, f"{path}.$ref"), root)
        _validate(instance, target, root, path)
        return

    if "const" in schema:
        expected_const = schema.get("const")
        if instance != expected_const:
            raise SchemaValidationError(
                path, f"expected the constant {expected_const!r}"
            )

    allowed = schema.get("enum")
    if allowed is not None and instance not in as_list(allowed, f"{path}.enum"):
        raise SchemaValidationError(path, f"{instance!r} is not one of {allowed!r}")

    declared_type = schema.get("type")
    if declared_type is not None:
        names = _type_names(declared_type, path)
        if not any(_matches_type(instance, name) for name in names):
            raise SchemaValidationError(
                path, f"expected type {names!r}, got {type(instance).__name__}"
            )

    if isinstance(instance, dict):
        _validate_object(instance, schema, root, path)
    elif isinstance(instance, list):
        _validate_array(instance, schema, root, path)
    elif isinstance(instance, str):
        _validate_string(instance, schema, path)
    elif isinstance(instance, (int, float)) and not isinstance(instance, bool):
        _validate_number(instance, schema, path)


def _validate_object(
    instance: Mapping[object, object],
    schema: Mapping[str, object],
    root: Mapping[str, object],
    path: str,
) -> None:
    properties_value = schema.get("properties")
    properties = (
        as_mapping(properties_value, f"{path}.properties")
        if properties_value is not None
        else {}
    )

    required_value = schema.get("required")
    if required_value is not None:
        for name in as_str_list(required_value, f"{path}.required"):
            if name not in instance:
                raise SchemaValidationError(path, f"missing required property {name!r}")

    additional = schema.get("additionalProperties", True)
    for raw_key, value in instance.items():
        key = as_str(raw_key, f"{path} key")
        if key in properties:
            child_schema = as_mapping(properties[key], f"{path}.{key}")
            _validate(value, child_schema, root, f"{path}.{key}")
        elif additional is False:
            raise SchemaValidationError(path, f"unexpected property {key!r}")
        elif isinstance(additional, dict):
            _validate(
                value,
                as_mapping(additional, f"{path}.additionalProperties"),
                root,
                f"{path}.{key}",
            )


def _validate_array(
    instance: list[object],
    schema: Mapping[str, object],
    root: Mapping[str, object],
    path: str,
) -> None:
    min_items = schema.get("minItems")
    if min_items is not None:
        minimum = _as_int_value(min_items, f"{path}.minItems")
        if len(instance) < minimum:
            raise SchemaValidationError(path, f"expected at least {minimum} items")

    max_items = schema.get("maxItems")
    if max_items is not None:
        maximum = _as_int_value(max_items, f"{path}.maxItems")
        if len(instance) > maximum:
            raise SchemaValidationError(path, f"expected at most {maximum} items")

    if schema.get("uniqueItems") is True and len(
        {_hashable(item) for item in instance}
    ) != len(instance):
        raise SchemaValidationError(path, "items must be unique")

    item_schema = schema.get("items")
    if item_schema is not None:
        items = as_mapping(item_schema, f"{path}.items")
        for index, item in enumerate(instance):
            _validate(item, items, root, f"{path}[{index}]")


def _validate_string(instance: str, schema: Mapping[str, object], path: str) -> None:
    min_length = schema.get("minLength")
    if min_length is not None and len(instance) < _as_int_value(
        min_length, f"{path}.minLength"
    ):
        raise SchemaValidationError(path, "string is too short")

    max_length = schema.get("maxLength")
    if max_length is not None and len(instance) > _as_int_value(
        max_length, f"{path}.maxLength"
    ):
        raise SchemaValidationError(path, "string is too long")

    pattern = schema.get("pattern")
    if (
        pattern is not None
        and re.search(as_str(pattern, f"{path}.pattern"), instance) is None
    ):
        raise SchemaValidationError(path, f"string does not match {pattern!r}")


def _validate_number(instance: float, schema: Mapping[str, object], path: str) -> None:
    minimum = schema.get("minimum")
    if minimum is not None and instance < _as_number_value(minimum, f"{path}.minimum"):
        raise SchemaValidationError(path, f"number is below the minimum {minimum!r}")

    maximum = schema.get("maximum")
    if maximum is not None and instance > _as_number_value(maximum, f"{path}.maximum"):
        raise SchemaValidationError(path, f"number is above the maximum {maximum!r}")


def _resolve_reference(
    reference: str, root: Mapping[str, object]
) -> Mapping[str, object]:
    if not reference.startswith("#/"):
        raise SchemaValidationError("$", f"unsupported schema reference {reference!r}")
    node: object = root
    for part in reference[2:].split("/"):
        mapping = as_mapping(node, reference)
        if part not in mapping:
            raise SchemaValidationError(
                "$", f"unresolved schema reference {reference!r}"
            )
        node = mapping[part]
    return as_mapping(node, reference)


def _type_names(value: object, path: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    return as_str_list(value, f"{path}.type")


def _matches_type(instance: object, name: str) -> bool:
    if name == "object":
        return isinstance(instance, dict)
    if name == "array":
        return isinstance(instance, list)
    if name == "string":
        return isinstance(instance, str)
    if name == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if name == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if name == "boolean":
        return isinstance(instance, bool)
    if name == "null":
        return instance is None
    return False


def _as_int_value(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValidationError(path, "expected an integer")
    return value


def _as_number_value(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaValidationError(path, "expected a number")
    return float(value)


def _hashable(value: object) -> object:
    if isinstance(value, dict):
        return tuple(sorted((str(key), _hashable(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_hashable(item) for item in value)
    return value
