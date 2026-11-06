"""Embeddings from Gemini, for the corpus and for contract clauses alike.

The corpus and the clauses must use the same model, or their vectors don't compare.
"""

import asyncio
from collections.abc import Sequence
from functools import cache
from typing import Any, Final, Literal

import numpy as np
import numpy.typing as npt
from django.conf import settings
from google import genai
from google.genai import types

from mbiu.corpus.snapshot import EMBEDDING_DIM
from mbiu.llm import ErrorCategory, LLMError
from mbiu.llm.gemini import _classify

Task = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "FACT_VERIFICATION"]

# Most texts the API takes in one request
BATCH: Final = 100


class GeminiEmbedder:
    """One embedding model, called with each text as its own input."""

    def __init__(self, client: Any, model_id: str, *, timeout_s: float = 30.0) -> None:
        """Wrap an SDK client; tests pass a fake one."""
        self._client = client
        self.model_id = model_id
        # An API model has no separate revision: the model ID is the version
        self.revision = model_id
        self._timeout_s = timeout_s

    async def embed(self, texts: Sequence[str], task: Task) -> npt.NDArray[np.float32]:
        """Return one unit-length row per text, or raise LLMError."""
        rows = []
        for batch in _batches(texts):
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.embed_content(
                        model=self.model_id, contents=_contents(batch), config=_config(task)
                    ),
                    timeout=self._timeout_s,
                )
            except TimeoutError:
                raise LLMError(ErrorCategory.TIMEOUT) from None
            except Exception as exc:
                raise _classify(exc) from None
            rows.append(_values(response))
        return _checked(rows, len(texts))

    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        """Embed corpus documents from synchronous code, such as the corpus pipeline.

        Uses the SDK's synchronous client: its async client stays bound to the first event
        loop, so repeated asyncio.run calls would fail.
        """
        config = _config("RETRIEVAL_DOCUMENT", timeout_ms=int(self._timeout_s * 1000))
        rows = []
        for batch in _batches(texts):
            try:
                response = self._client.models.embed_content(
                    model=self.model_id, contents=_contents(batch), config=config
                )
            except Exception as exc:
                raise _classify(exc) from None
            rows.append(_values(response))
        return _checked(rows, len(texts))


def _batches(texts: Sequence[str]) -> list[Sequence[str]]:
    return [texts[i : i + BATCH] for i in range(0, len(texts), BATCH)]


def _contents(batch: Sequence[str]) -> list[types.Content]:
    # A plain list of strings would come back as ONE combined embedding
    return [types.Content(parts=[types.Part(text=t)]) for t in batch]


def _config(task: Task, *, timeout_ms: int | None = None) -> types.EmbedContentConfig:
    return types.EmbedContentConfig(
        task_type=task,
        output_dimensionality=EMBEDDING_DIM,
        http_options=types.HttpOptions(timeout=timeout_ms) if timeout_ms else None,
    )


def _values(response: Any) -> npt.NDArray[np.float32]:
    return np.array([e.values for e in response.embeddings], dtype=np.float32)


def _checked(rows: list[npt.NDArray[np.float32]], count: int) -> npt.NDArray[np.float32]:
    """One finite 768-d row per text, scaled to unit length."""
    vectors = np.concatenate(rows) if rows else np.empty((0, EMBEDDING_DIM), dtype=np.float32)
    if vectors.shape != (count, EMBEDDING_DIM) or not np.isfinite(vectors).all():
        raise LLMError(ErrorCategory.SCHEMA_INVALID)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if (norms == 0).any():
        raise LLMError(ErrorCategory.SCHEMA_INVALID)
    return (vectors / norms).astype(np.float32)


@cache
def embedder() -> GeminiEmbedder:
    """The process-wide embedder."""
    if not settings.GEMINI_API_KEY:
        raise LLMError(ErrorCategory.UNAVAILABLE)
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=0)),
    )
    return GeminiEmbedder(client, settings.EMBEDDING_MODEL_ID, timeout_s=settings.BATCH_TIMEOUT_S)
