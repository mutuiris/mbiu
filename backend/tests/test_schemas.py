import json
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from mbiu.api import openapi, schemas

CLAUSE_RESULT: dict[str, Any] = {
    "clause_id": "c-7-2",
    "pages": [4],
    "original_text": "The Label shall pay the Artist 8% of net receipts.",
    "status": "evaluated",
    "comparison": "worse_for_you",
    "headline": "You could earn very little from your songs for years",
    "what_it_says": "You get 8% of what is left after costs.",
    "what_it_means": "Costs come off first, so your share shrinks.",
    "comparison_note": None,
    "impact_inputs": None,
    "linked_clauses": [],
    "fairer_wording": None,
    "ask_them": "Can the royalty be 15% of gross receipts?",
    "standard_template_id": None,
    "standard_excerpt": None,
    "evidence": [],
    "evidence_ids": [],
    "evidence_quote": None,
    "provider": "gemini",
    "model_version": "gemini-3.8-flash",
}

PAYLOADS: dict[type[BaseModel], dict[str, Any]] = {
    schemas.DocumentEvent: {"page_count": 1, "sections": [], "clauses": [], "skipped_pages": []},
    schemas.ContractMapEvent: {"contract_type": None, "links": [], "issues": []},
    schemas.ProgressEvent: {"stage": "compare", "done": 1, "total": 4},
    schemas.ClauseResultEvent: CLAUSE_RESULT,
    schemas.ClauseUpdatedEvent: CLAUSE_RESULT,
    schemas.ClauseFailedEvent: {"clause_id": "c-1", "reason": "timeout", "retryable": True},
    schemas.HeartbeatEvent: {},
    schemas.DoneEvent: {
        "top_asks": [],
        "contract_issues": [],
        "missing_protections": [],
        "good_news": [],
        "matches_count": 0,
        "skipped_pages": [],
        "ask_list": [],
        "versions": {"schema_version": "1", "prompt": "compare_v1", "model": "m", "corpus": "1"},
    },
}


def event(model: type[BaseModel]) -> dict[str, Any]:
    return {
        "type": model.model_fields["type"].default,
        "schema_version": "1",
        "payload": PAYLOADS[model],
    }


@pytest.mark.parametrize("model", PAYLOADS, ids=lambda m: m.__name__)
def test_every_event_round_trips_through_the_union(model: type[BaseModel]) -> None:
    parsed = schemas.stream_event.validate_json(json.dumps(event(model)))
    assert isinstance(parsed, model)
    assert json.loads(parsed.model_dump_json()) == event(model)


@pytest.mark.parametrize("model", PAYLOADS, ids=lambda m: m.__name__)
def test_every_event_rejects_unknown_fields(model: type[BaseModel]) -> None:
    with pytest.raises(ValidationError):
        schemas.stream_event.validate_python({**event(model), "surprise": 1})


@pytest.mark.parametrize("model", PAYLOADS, ids=lambda m: m.__name__)
def test_every_event_rejects_a_missing_payload(model: type[BaseModel]) -> None:
    body = event(model)
    del body["payload"]
    with pytest.raises(ValidationError):
        schemas.stream_event.validate_python(body)


def test_rejects_another_schema_version() -> None:
    with pytest.raises(ValidationError):
        schemas.stream_event.validate_python(
            {**event(schemas.HeartbeatEvent), "schema_version": "2"}
        )


def test_rejects_unknown_event_types() -> None:
    with pytest.raises(ValidationError):
        schemas.stream_event.validate_python(
            {"type": "mystery", "schema_version": "1", "payload": {}}
        )


def test_clause_result_rejects_a_missing_required_field() -> None:
    body = {k: v for k, v in CLAUSE_RESULT.items() if k != "headline"}
    with pytest.raises(ValidationError):
        schemas.ClauseResult.model_validate(body)


def test_summary_keeps_at_most_three_top_asks() -> None:
    asks = [{"clause_id": "c-1", "question": "Can it be 30 days?"}] * 4
    with pytest.raises(ValidationError):
        schemas.Summary.model_validate({**PAYLOADS[schemas.DoneEvent], "top_asks": asks})


def test_openapi_document_is_stable_and_has_no_defaults_on_fixed_values() -> None:
    first, second = openapi.build(), openapi.build()
    assert first == second
    components = first["components"]["schemas"]
    assert "StreamEvent" in components and "ApiError" in components
    assert "default" not in json.dumps(components["HeartbeatEvent"]["properties"]["type"])
    assert components["HeartbeatEvent"]["required"] == ["type", "schema_version", "payload"]
