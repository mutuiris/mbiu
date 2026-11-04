"""Typed helpers for reading and writing the small JSON documents used by evals."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path


class JsonShapeError(ValueError):
    """Raised when a JSON document does not have the shape the gate expects."""


def as_mapping(value: object, path: str) -> Mapping[str, object]:
    """Return ``value`` as a string-keyed mapping or raise ``JsonShapeError``."""
    if not isinstance(value, dict):
        raise JsonShapeError(f"{path}: expected an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise JsonShapeError(f"{path}: object keys must be strings")
        result[key] = item
    return result


def as_list(value: object, path: str) -> list[object]:
    """Return ``value`` as a list or raise ``JsonShapeError``."""
    if not isinstance(value, list):
        raise JsonShapeError(f"{path}: expected an array")
    return value


def as_str(value: object, path: str) -> str:
    """Return ``value`` as a string or raise ``JsonShapeError``."""
    if not isinstance(value, str):
        raise JsonShapeError(f"{path}: expected a string")
    return value


def as_optional_str(value: object, path: str) -> str | None:
    """Return ``value`` as a string, or ``None`` when it is null or absent."""
    if value is None:
        return None
    return as_str(value, path)


def as_int(value: object, path: str) -> int:
    """Return ``value`` as an integer, rejecting booleans."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise JsonShapeError(f"{path}: expected an integer")
    return value


def as_str_list(value: object, path: str) -> tuple[str, ...]:
    """Return ``value`` as a tuple of strings."""
    return tuple(
        as_str(item, f"{path}[{index}]")
        for index, item in enumerate(as_list(value, path))
    )


def as_int_list(value: object, path: str) -> tuple[int, ...]:
    """Return ``value`` as a tuple of integers."""
    return tuple(
        as_int(item, f"{path}[{index}]")
        for index, item in enumerate(as_list(value, path))
    )


def load_json(path: Path) -> object:
    """Load a JSON document from ``path``."""
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: object) -> None:
    """Write ``payload`` as stable, readable JSON with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


def dumps_compact(payload: object) -> str:
    """Serialise ``payload`` for embedding in a prompt or JSONL row."""
    return json.dumps(payload, ensure_ascii=True, sort_keys=False)
