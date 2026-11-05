"""Promptfoo provider that runs the golden set through Mbiu's evaluation prompt.

Modes (``MBIU_EVAL_MODE`` or ``options.config.mode``):

``auto``       Gemini when an API key is present, otherwise the reference evaluator.
``gemini``     Send the rendered prompt to Gemini and parse its JSON.
``reference``  Deterministic fixed rules; no network. Used for hermetic CI.
``lenient``    Simulate the deliberately broken prompt fixture; used to prove
               that the gate blocks it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.generator.jsonutil import as_list, as_mapping, as_str, load_json
from evals.generator.models import (
    ContractPrediction,
    GoldenContract,
)
from evals.generator.reference_evaluator import (
    evaluate_contract,
    lenient_prediction,
)

EVALS_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = EVALS_DIR / "datasets"
LENIENT_PROMPT_FILE = (
    Path(__file__).resolve().parent / "prompts" / "lenient_clause_eval.txt"
)
DEFAULT_MODEL = "gemini-2.5-flash"


def _config(options: Mapping[str, object]) -> Mapping[str, object]:
    config = options.get("config")
    return as_mapping(config, "options.config") if config is not None else {}


def _variables(context: Mapping[str, object]) -> Mapping[str, object]:
    variables = context.get("vars")
    if variables is None:
        return {}
    return as_mapping(variables, "context.vars")


def _expected_contract(variables: Mapping[str, object]) -> GoldenContract:
    expected_file = as_str(variables.get("expected_file"), "vars.expected_file")
    return GoldenContract.from_dict(load_json(DATASETS_DIR / expected_file))


def _mode(config: Mapping[str, object]) -> str:
    configured = os.environ.get("MBIU_EVAL_MODE")
    if configured:
        return configured
    value = config.get("mode", "auto")
    return as_str(value, "config.mode") if value is not None else "auto"


def _model(config: Mapping[str, object]) -> str:
    value = os.environ.get("GEMINI_MODEL") or config.get("model") or DEFAULT_MODEL
    return as_str(value, "config.model")


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or None


def _parse_model_output(text: str, contract_id: str) -> ContractPrediction:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model output contains no JSON object")
    payload: object = json.loads(stripped[start : end + 1])
    return ContractPrediction.from_dict(payload, contract_id=contract_id)


def _gemini_text(prompt: str, model: str, api_key: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        parsed: object = json.loads(response.content.decode("utf-8"))
    data = as_mapping(parsed, "$")
    candidates = as_list(data.get("candidates"), "$.candidates")
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    candidate = as_mapping(candidates[0], "$.candidates[0]")
    content = as_mapping(candidate.get("content"), "$.candidates[0].content")
    parts = as_list(content.get("parts"), "$.candidates[0].content.parts")
    texts: list[str] = []
    for index, part in enumerate(parts):
        part_data = as_mapping(part, f"$.candidates[0].content.parts[{index}]")
        text = part_data.get("text")
        if isinstance(text, str):
            texts.append(text)
    if not texts:
        raise ValueError("Gemini returned no text parts")
    return "".join(texts)


def _prediction_payload(
    mode: str,
    prompt: str,
    contract: GoldenContract,
    config: Mapping[str, object],
) -> ContractPrediction:
    if mode in {"lenient", "broken"}:
        LENIENT_PROMPT_FILE.read_text(encoding="utf-8")
        return lenient_prediction(contract)
    if mode == "reference":
        return evaluate_contract(contract)
    if mode != "gemini":
        raise ValueError(f"unknown MBIU_EVAL_MODE {mode!r}")
    api_key = _api_key()
    if api_key is None:
        raise ValueError("Gemini mode requires GEMINI_API_KEY or GOOGLE_API_KEY")
    model = _model(config)
    return _parse_model_output(
        _gemini_text(prompt, model, api_key), contract.contract_id
    )


def call_api(
    prompt: str,
    options: Mapping[str, object],
    context: Mapping[str, object],
) -> dict[str, object]:
    """Promptfoo Python-provider entry point."""
    config = _config(options)
    variables = _variables(context)
    try:
        contract = _expected_contract(variables)
        mode = _mode(config)
        if mode == "auto":
            mode = "gemini" if _api_key() is not None else "reference"
        prediction = _prediction_payload(mode, prompt, contract, config)
    except (OSError, httpx.HTTPError, ValueError, TypeError) as error:
        return {"error": f"golden-set provider failed: {error}"}

    metadata: dict[str, object] = {
        "mode": mode,
        "contract_id": contract.contract_id,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
    if mode == "gemini":
        metadata["model"] = _model(config)
    return {
        "output": json.dumps(prediction.to_dict(), indent=2, ensure_ascii=True),
        "metadata": metadata,
    }
