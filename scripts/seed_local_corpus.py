"""Seed local synthetic template corpus.

Exports the synthetic template corpus used for local development and testing.
Can be executed as a script or imported.
"""

import sys
from pathlib import Path

# Add backend to sys.path so we can import synthetic corpus models
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mbiu.corpus.synthetic import SYNTHETIC_CORPUS, retrieve_simple_evidence


def main() -> None:
    """Print the synthetic corpus summary."""
    print(f"Loaded {len(SYNTHETIC_CORPUS)} synthetic template clauses for local testing:")
    for template in SYNTHETIC_CORPUS:
        print(f" - [{template.template_id}] {template.topic}: {template.source_title}")


if __name__ == "__main__":
    main()
