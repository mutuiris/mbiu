"""Clause topics and the order an artist should see them in: what affects them most first."""

from typing import Final, get_args

import numpy as np
import numpy.typing as npt

from mbiu.pipeline.tag import Topic

TOPICS: Final[tuple[str, ...]] = get_args(Topic)

# Lower comes first: money, ownership, term, exclusivity, termination, then the rest,
# with definitions, governing law and boilerplate (notices, signatures) last
IMPACT_RANK: Final[dict[str, int]] = {
    "royalties": 0,
    "payment": 0,
    "advances_recoupment": 0,
    "accounting_audit": 0,
    "grant_of_rights": 1,
    "moral_rights": 1,
    "term": 2,
    "exclusivity": 3,
    "termination": 4,
    "warranties_indemnities": 5,
    "credit": 5,
    "dispute_resolution": 5,
    "definitions": 6,
    "governing_law": 7,
    "boilerplate": 7,
}
_UNKNOWN_RANK: Final = 5

# A few plain examples per topic. A clause gets the topic of its nearest example.
TOPIC_EXAMPLES: Final[dict[str, tuple[str, ...]]] = {
    "royalties": (
        "The Company shall pay the Artist a royalty on receipts from sales and streams.",
        "Royalties are calculated on net receipts after distribution costs.",
    ),
    "payment": (
        "Payments are due within thirty days of the end of each quarter.",
        "The fee is payable by bank transfer on signing.",
    ),
    "advances_recoupment": (
        "The advance is recoupable from the Artist's royalties.",
        "Recording costs are recouped before any royalty is paid.",
    ),
    "accounting_audit": (
        "The Company shall send royalty statements twice a year.",
        "The Artist may audit the Company's books once a year.",
    ),
    "grant_of_rights": (
        "The Artist assigns to the Company all rights in the master recordings.",
        "The Company owns the copyright in the recordings throughout the world.",
    ),
    "moral_rights": ("The Artist waives all moral rights in the works.",),
    "term": (
        "This Agreement lasts for two years from the date of signing.",
        "The Company may extend the term by option periods.",
    ),
    "exclusivity": (
        "The Artist shall not record for any other label during the term.",
        "The Artist's services are exclusive to the Company.",
    ),
    "termination": (
        "Either party may end this Agreement with sixty days' written notice.",
        "The Company may terminate if the Artist breaches this Agreement.",
    ),
    "warranties_indemnities": (
        "The Artist warrants that the recordings do not infringe any rights.",
        "The Artist shall indemnify the Company against all claims.",
    ),
    "credit": ("The Artist shall be credited on all releases.",),
    "dispute_resolution": ("Any dispute shall be referred to arbitration.",),
    "definitions": ('In this Agreement "Net Receipts" means money received after costs.',),
    "governing_law": ("This Agreement is governed by the laws of Kenya.",),
    "boilerplate": (
        "Notices must be in writing and sent to the addresses above.",
        "This Agreement may be signed in counterparts.",
        "Signed by the parties on the date below.",
    ),
}


def impact_rank(topic: str | None) -> int:
    """Where a clause about this topic goes in the artist's reading order (lower is earlier)."""
    return IMPACT_RANK.get(topic or "", _UNKNOWN_RANK)


def classify(
    clause_vector: npt.NDArray[np.float32],
    example_vectors: npt.NDArray[np.float32],
    example_topics: tuple[str, ...],
) -> str:
    """Topic of the nearest example. Vectors are unit length, so a dot product is cosine."""
    return example_topics[int(np.argmax(example_vectors @ clause_vector))]
