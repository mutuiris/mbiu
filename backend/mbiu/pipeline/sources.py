"""Load and validate the public source list from ``corpus/sources.yaml``."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from mbiu.pipeline.errors import SourceConfigError
from mbiu.pipeline.models import Source

_REQUIRED_FIELDS = ("url", "licence", "reviewing_body", "contract_type", "jurisdiction")


def load_sources(path: Path) -> list[Source]:
    """Read and validate every source in ``path``.

    Args:
        path: Path to the YAML source list.

    Returns:
        Validated sources in file order.

    Raises:
        SourceConfigError: If the file cannot be read or an entry is invalid.
    """
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SourceConfigError(f"cannot read sources file: {path}") from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise SourceConfigError("sources file is not valid YAML") from exc

    if data is None:
        return []
    if not isinstance(data, Mapping):
        raise SourceConfigError("sources file must contain a 'sources' list")

    raw_sources = data.get("sources")
    if raw_sources is None:
        return []
    if not isinstance(raw_sources, list):
        raise SourceConfigError("'sources' must be a list")

    return [_parse_source(item, index) for index, item in enumerate(raw_sources, start=1)]


def _parse_source(raw: Any, index: int) -> Source:
    if not isinstance(raw, Mapping):
        raise SourceConfigError(f"source {index} must be a mapping")

    values: dict[str, str] = {}
    for name in _REQUIRED_FIELDS:
        values[name] = _required_text(raw, name, index)

    raw_version = raw.get("template_version", "1")
    if isinstance(raw_version, int) and not isinstance(raw_version, bool):
        version = str(raw_version)
    elif isinstance(raw_version, str) and raw_version.strip():
        version = raw_version.strip()
    else:
        raise SourceConfigError(f"source {index} has an invalid 'template_version'")

    url = values["url"]
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise SourceConfigError(f"source {index} has an invalid 'url'")

    return Source(
        url=url,
        licence=values["licence"],
        reviewing_body=values["reviewing_body"],
        contract_type=values["contract_type"],
        jurisdiction=values["jurisdiction"],
        template_version=version,
    )


def _required_text(raw: Mapping[Any, Any], name: str, index: int) -> str:
    value = raw.get(name)
    if not isinstance(value, str) or not value.strip():
        raise SourceConfigError(f"source {index} is missing required field '{name}'")
    return value.strip()
