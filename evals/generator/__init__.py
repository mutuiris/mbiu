"""Synthetic golden-set generation and the Mbiu quality gate.

The package builds synthetic music contracts with risks that are known by
construction, stores the expected outcome next to each PDF, and refuses any
evaluation result that labels a planted risk as ``matches_standard`` without a
flag. Nothing in this package talks to a live model unless the caller asks for
Gemini explicitly.
"""

from __future__ import annotations

GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = 1

__all__ = ["GENERATOR_VERSION", "SCHEMA_VERSION"]
