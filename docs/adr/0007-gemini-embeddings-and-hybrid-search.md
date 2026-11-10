# 0007. Gemini embeddings with hybrid search

**Status:** Accepted

## Context

Each clause has to be matched with the right reference text. Pure keyword search misses clauses that use different words for the same thing; pure vector search can miss exact terms such as "cross-collateralization".

## Decision

- Reference chunks and contract clauses are embedded with the same model, `gemini-embedding-2` (`EMBEDDING_MODEL_ID`), so they're comparable.
- Retrieval combines vector similarity with BM25 keyword search and merges the two rankings (`backend/mbiu/retrieval/search.py`), preferring Kenyan sources first.
- The active corpus is loaded into memory once per API process, so a check never queries the database for retrieval.

## Consequences

- Changing the embedding model means re-embedding the whole corpus: publish a new corpus version with the new model.
- A change to the active corpus takes effect when the API restarts (a deploy, or Render waking from sleep).
- If the embeddings API is down, retrieval falls back to keyword search alone.
