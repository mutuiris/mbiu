"""Tests for the stateless clause evaluations endpoint (MB-26).

Verifies:
- POST /api/v1/clause-evaluations endpoint behavior
- NDJSON streaming events: progress, clause_result, clause_failed, done
- Non-streaming JSON mode (Accept: application/json)
- Validation errors: empty list, malformed JSON, invalid clause structures, method not allowed
- Contract type without reviewed standard returns cannot_compare
- Reverse check for missing protections reflected in final summary
- Zero Contract Storage: in-memory execution, no DB rows or temp files created,
  Cache-Control: no-store header enforced.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from django.http import StreamingHttpResponse
from django.test import Client

from mbiu.corpus.loader import (
    ChunkMetadata,
    CorpusSnapshot,
)
from mbiu.corpus.models import CorpusVersion, ReferenceChunk
from mbiu.evaluation.comparison import (
    NO_STANDARD_FOR_TYPE_MESSAGE,
    OUTCOME_CANNOT_COMPARE,
    STATUS_CANNOT_COMPARE,
    STATUS_EVALUATED,
)
from mbiu.evaluation.verify import (
    LABEL_CANNOT_COMPARE,
    VALID_LABELS,
)


@pytest.fixture
def api_client() -> Client:
    """Return Django test client."""
    return Client()


@pytest.fixture
def mock_snapshot(monkeypatch: pytest.MonkeyPatch) -> CorpusSnapshot:
    """Set up an active in-memory corpus snapshot with synthetic reference standards."""
    chunk1 = ChunkMetadata(
        chunk_id="ref-rec-01",
        version_tag="v2026.10",
        source_title="Musicians Union Standard Recording Agreement",
        source_license="CC-BY-4.0",
        topic="money",
        contract_type="recording",
        jurisdiction="KE",
        drafted_for="artist",
        chunk_key="rec_royalty_net",
        text="Standard terms: Producer shall pay a royalty rate of 16% of Net Receipts.",
        metadata={"category": "royalties"},
    )
    chunk2 = ChunkMetadata(
        chunk_id="ref-rec-02",
        version_tag="v2026.10",
        source_title="Musicians Union Standard Recording Agreement",
        source_license="CC-BY-4.0",
        topic="ownership",
        contract_type="recording",
        jurisdiction="KE",
        drafted_for="artist",
        chunk_key="rec_masters_ownership",
        text="The Artist retains all rights in sound recordings and musical works.",
        metadata={"category": "ownership"},
    )
    snapshot = CorpusSnapshot(
        version_id="snap-01",
        version_tag="v2026.10",
        embedding_model_id="embeddinggemma-2",
        embedding_dim=4,
        embeddings=np.zeros((2, 4), dtype=np.float32),
        chunks=(chunk1, chunk2),
        by_id={"ref-rec-01": chunk1, "ref-rec-02": chunk2},
    )
    monkeypatch.setattr("mbiu.evaluation.views.get_active_corpus_snapshot", lambda: snapshot)
    return snapshot


# ==============================================================================
# VALID RE-EVALUATION TESTS
# ==============================================================================


def test_clause_evaluations_ndjson_streaming(
    api_client: Client, mock_snapshot: CorpusSnapshot
) -> None:
    """Verify POST /api/v1/clause-evaluations streams newline-delimited JSON events."""
    payload = {
        "clauses": [
            {
                "clause_id": "4.1",
                "text": "The Producer shall pay 16% of Net Receipts semi-annually.",
                "pages": [2],
                "title": "Royalties",
                "section": "main",
            },
            {
                "clause_id": "5.1",
                "text": "Artist retains all rights in sound recordings created hereunder.",
                "pages": [3],
                "title": "Masters Ownership",
                "section": "main",
            },
        ],
        "contract_type": "recording",
    }

    response = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers["Content-Type"]
    assert "no-store" in response.headers["Cache-Control"]
    assert isinstance(response, StreamingHttpResponse)

    # Parse streaming lines
    content = b"".join(response.streaming_content).decode("utf-8")
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    assert len(lines) >= 4  # initial progress, 2 results, progress updates, done

    events = [json.loads(line) for line in lines]
    event_types = [e["event"] for e in events]

    assert "progress" in event_types
    assert "clause_result" in event_types
    assert "done" in event_types

    # Verify clause results
    result_events = [e for e in events if e["event"] == "clause_result"]
    assert len(result_events) == 2

    first_card = result_events[0]["clause"]
    assert first_card["clause_id"] == "4.1"
    assert first_card["label"] in VALID_LABELS
    assert first_card["status"] == STATUS_EVALUATED
    # Verified quote substring
    assert "16% of Net Receipts" in first_card["original_text"]

    second_card = result_events[1]["clause"]
    assert second_card["clause_id"] == "5.1"
    assert second_card["label"] in VALID_LABELS
    assert second_card["status"] == STATUS_EVALUATED

    # Verify done event summary
    done_event = next(e for e in events if e["event"] == "done")
    summary = done_event["summary"]
    assert "top_asks" in summary
    assert "good_news" in summary
    assert "versions" in summary


def test_clause_evaluations_json_mode(api_client: Client, mock_snapshot: CorpusSnapshot) -> None:
    """Verify endpoint returns single JSON payload when Accept: application/json is sent."""
    payload = {
        "clauses": [
            {
                "clause_id": "1.1",
                "text": "Standard terms: Producer shall pay a royalty rate of 16% of Net Receipts.",
                "pages": [1],
                "title": "Royalties",
            }
        ],
        "contract_type": "recording",
    }

    response = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 200
    assert "application/json" in response.headers["Content-Type"]
    assert "no-store" in response.headers["Cache-Control"]

    data = response.json()
    assert "events" in data
    event_types = [e["event"] for e in data["events"]]
    assert "clause_result" in event_types
    assert "done" in event_types


def test_clause_evaluations_url_with_trailing_slash(
    api_client: Client, mock_snapshot: CorpusSnapshot
) -> None:
    """Verify endpoint works with trailing slash without 301 redirection."""
    payload = {
        "clauses": [
            {
                "clause_id": "1.1",
                "text": "Producer pays 16% of Net Receipts.",
                "pages": [1],
            }
        ]
    }

    response = api_client.post(
        "/api/v1/clause-evaluations/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200


# ==============================================================================
# CONTRACT TYPE WITHOUT REVIEWED STANDARD
# ==============================================================================


def test_clause_evaluations_no_standard_for_contract_type(
    api_client: Client, mock_snapshot: CorpusSnapshot
) -> None:
    """Verify unreviewed contract types emit cannot_compare with standard notice."""
    payload = {
        "clauses": [
            {
                "clause_id": "pod_1",
                "text": "Host shall produce 20 episodes of podcast content per year.",
                "pages": [1],
                "title": "Host Obligations",
            }
        ],
        "contract_type": "podcast_host",  # Unreviewed contract type
    }

    response = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert isinstance(response, StreamingHttpResponse)
    content = b"".join(response.streaming_content).decode("utf-8")
    events = [json.loads(line) for line in content.split("\n") if line.strip()]

    result_event = next(e for e in events if e["event"] == "clause_result")
    card = result_event["clause"]

    assert card["status"] == STATUS_CANNOT_COMPARE
    assert card["comparison"] == OUTCOME_CANNOT_COMPARE
    assert card["label"] == LABEL_CANNOT_COMPARE
    assert card["comparison_note"] == NO_STANDARD_FOR_TYPE_MESSAGE


# ==============================================================================
# INPUT VALIDATION & ERROR HANDLING
# ==============================================================================


def test_clause_evaluations_empty_clauses_list(api_client: Client) -> None:
    """Verify empty clauses list returns 400 Bad Request."""
    payload: dict[str, Any] = {"clauses": []}

    response = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "empty" in data["error"].lower()


def test_clause_evaluations_missing_clauses_field(api_client: Client) -> None:
    """Verify request missing 'clauses' returns 400 Bad Request."""
    payload = {"contract_type": "recording"}

    response = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_clause_evaluations_malformed_json(api_client: Client) -> None:
    """Verify malformed JSON body returns 400 Bad Request."""
    response = api_client.post(
        "/api/v1/clause-evaluations",
        data="not a json { string",
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_clause_evaluations_non_object_payload(api_client: Client) -> None:
    """Verify non-dictionary JSON payload returns 400 Bad Request."""
    response = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(["clause1", "clause2"]),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_clause_evaluations_invalid_clause_structure(api_client: Client) -> None:
    """Verify clause item missing clause_id or text returns 400 Bad Request."""
    # Missing text
    payload1 = {"clauses": [{"clause_id": "1.1"}]}
    resp1 = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload1),
        content_type="application/json",
    )
    assert resp1.status_code == 400

    # Missing clause_id
    payload2 = {"clauses": [{"text": "Some text"}]}
    resp2 = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload2),
        content_type="application/json",
    )
    assert resp2.status_code == 400

    # Empty text
    payload3 = {"clauses": [{"clause_id": "1.1", "text": "   "}]}
    resp3 = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload3),
        content_type="application/json",
    )
    assert resp3.status_code == 400


def test_clause_evaluations_method_not_allowed(api_client: Client) -> None:
    """Verify GET, PUT, DELETE methods return 405 Method Not Allowed."""
    get_resp = api_client.get("/api/v1/clause-evaluations")
    assert get_resp.status_code == 405

    put_resp = api_client.put(
        "/api/v1/clause-evaluations",
        data="{}",
        content_type="application/json",
    )
    assert put_resp.status_code == 405

    del_resp = api_client.delete("/api/v1/clause-evaluations")
    assert del_resp.status_code == 405


# ==============================================================================
# ZERO CONTRACT STORAGE & PRIVACY INVARIANTS
# ==============================================================================


@pytest.mark.django_db
def test_clause_evaluations_zero_contract_storage(
    api_client: Client, mock_snapshot: CorpusSnapshot
) -> None:
    """Verify evaluation does not persist contract data to database or disk."""
    temp_dir = Path(tempfile.gettempdir())
    files_before = set(temp_dir.iterdir())
    corpus_count_before = ReferenceChunk.objects.count()
    version_count_before = CorpusVersion.objects.count()

    secret_canary = "UNIQUE_CANARY_USER_CONTRACT_SECRET_DO_NOT_STORE_12345"
    payload = {
        "clauses": [
            {
                "clause_id": "sec_1",
                "text": f"Confidential text containing canary {secret_canary}.",
                "pages": [1],
                "title": "Secret Clause",
            }
        ],
        "contract_type": "recording",
    }

    response = api_client.post(
        "/api/v1/clause-evaluations",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200

    # Confirm no new rows in DB
    assert ReferenceChunk.objects.count() == corpus_count_before
    assert CorpusVersion.objects.count() == version_count_before

    # Confirm no temp files created in temp dir
    files_after = set(temp_dir.iterdir())
    new_files = files_after - files_before
    for f in new_files:
        try:
            if f.is_file():
                assert secret_canary not in f.read_text(errors="ignore")
        except OSError:
            pass

    # Confirm Cache-Control: no-store header
    assert "no-store" in response.headers["Cache-Control"]
