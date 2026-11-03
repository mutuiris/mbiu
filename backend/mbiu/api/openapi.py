"""
Write the API contract as an OpenAPI document, the input for the frontend's type generator.

Usage: python -m mbiu.api.openapi <output.json>
"""

import json
import sys
from pathlib import Path
from typing import Any

from pydantic.json_schema import models_json_schema

from mbiu.api import schemas

REF = "#/components/schemas/{model}"


def _drop_const_defaults(node: Any) -> None:
    # Fixed values like `type` and `schema_version` have Python defaults for convenience.
    # Left in, the generated Zod schemas would accept events that leave them out.
    if isinstance(node, dict):
        if "const" in node:
            node.pop("default", None)
        for value in node.values():
            _drop_const_defaults(value)
    elif isinstance(node, list):
        for value in node:
            _drop_const_defaults(value)


def build() -> dict[str, Any]:
    """Return the OpenAPI document. Endpoint paths join it once the API has routes."""
    _, top = models_json_schema([(schemas.ApiError, "serialization")], ref_template=REF)
    event = schemas.stream_event.json_schema(mode="serialization", ref_template=REF)
    components = {**top.get("$defs", {}), **event.pop("$defs", {})}
    components["StreamEvent"] = event
    _drop_const_defaults(components)
    return {
        "openapi": "3.1.0",
        "info": {"title": "Mbiu API", "version": schemas.SCHEMA_VERSION},
        "paths": {},
        "components": {"schemas": dict(sorted(components.items()))},
    }


def main() -> None:
    """Write the document to the path given on the command line."""
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
