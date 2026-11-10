# Mbiu API

The browser talks to the Mbiu API (Django on ASGI, hosted on Render) over four endpoints. Contract checks are streamed back as newline-delimited JSON (NDJSON), one event per line, so results appear as each clause finishes.

The exact shapes of every request, event and error are generated from the backend models (`backend/mbiu/api/schemas.py`) into [`frontend/src/lib/api/openapi.json`](../frontend/src/lib/api/openapi.json) and TypeScript types (`frontend/src/lib/api/generated/`). Run `just types` after changing a model; CI fails if the generated files are out of date. This page explains how the pieces fit together; the schema is the source of truth for field types.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/evaluations` | Upload a contract PDF and stream its results |
| `POST` | `/api/v1/clause-evaluations` | Check clauses again (a retry, or the clauses not checked yet) and stream their results |
| `GET` | `/healthz` | The process is up |
| `GET` | `/readyz` | The database and the reference corpus are usable |

## Privacy rules every client must keep

- The contract is read in memory and never stored. Don't add logging, caching or analytics that capture request bodies or clause text.
- Clause text is sent to the AI provider with storage turned off (`store=False`); see [data-transfers.md](data-transfers.md).
- Use synthetic contracts only when testing (`evals/datasets/pdfs/`, `evals/sample_contracts/pdf/`).

## Bot check (Turnstile)

Both `POST` endpoints require a Cloudflare Turnstile token. The API verifies it with Cloudflare before doing any work and fails closed: a missing, invalid or already-used token returns `400 bot_check_failed`.

- A token works **once**. Get a new one from the widget before every request, including retries.
- `/api/v1/evaluations` reads the token from the form field `turnstile_token` (also accepted: `cf-turnstile-response`, or the `X-Turnstile-Token` header).
- `/api/v1/clause-evaluations` reads it from the JSON body field `turnstile_token`.

## `POST /api/v1/evaluations`

Upload a contract and stream the full check.

**Request:** `multipart/form-data`

| Field | Required | Notes |
|---|---|---|
| `file` | yes | The contract as a PDF (`pdf` is accepted as the field name too) |
| `turnstile_token` | yes | See [Bot check](#bot-check-turnstile) |

Optional header: `traceparent` (W3C trace context) to join the browser's trace.

**Limits** (environment settings on the API):

| Setting | Default | Refused with |
|---|---|---|
| `MAX_UPLOAD_MB` | 10 | `file_too_large` |
| `MAX_PAGES` | 40 | `too_many_pages` |

The file must be a real, unencrypted PDF with a text layer: `invalid_file_type`, `encrypted_pdf` and `scanned_pdf` cover the other cases.

**Response:**

- `200` with `Content-Type: application/x-ndjson`: the [event stream](#the-event-stream).
- `400` or `503` with `Content-Type: application/json`: an [error](#errors) if the request is refused before the stream starts.

## `POST /api/v1/clause-evaluations`

Check clauses the browser already holds, without uploading the PDF again: retrying a failed clause, or checking the clauses the first pass left unchecked.

**Request:** `application/json`

```json
{
  "turnstile_token": "<fresh token>",
  "clauses": [
    {
      "clause_id": "7.2",
      "section_id": "main",
      "number": "7.2",
      "heading": "Royalties",
      "text": "Company shall pay Artist a royalty of 12% of Net Receipts…",
      "pages": [4],
      "start": 10240,
      "end": 10512
    }
  ]
}
```

`clauses` holds at least one clause, copied unchanged from the `document` event of the original stream.

**Response:** the same NDJSON stream, with only `progress`, `heartbeat`, `clause_result` and `clause_failed` events. There is no `document`, `contract_map` or `done` event. A malformed body returns `400 invalid_request`.

## The event stream

Every line is one JSON object:

```json
{"type": "clause_result", "schema_version": "1", "payload": { … }}
```

| `type` | `payload` | When |
|---|---|---|
| `document` | `DocumentPayload`: `page_count`, `sections`, `clauses` (each with `clause_id`, `number`, `heading`, `text`, `pages`, `start`, `end`), `skipped_pages` | First event, once the PDF is split into clauses |
| `heartbeat` | `{}` | Every 10 seconds while work continues, so proxies and the browser keep the connection open. Ignore it. |
| `contract_map` | `ContractMapPayload`: `contract_type`, `links` between clauses, `issues` (clauses that conflict with or override each other, with both quotes) | After the whole-contract check |
| `progress` | `Progress`: `stage`, `done`, `total` | As clauses finish |
| `clause_result` | `ClauseResult` | One per clause that was checked |
| `clause_updated` | `ClauseResult` | A clause whose result changed after the whole-contract check. **Replace** the earlier result; if the client has none for that clause (for example after restoring kept results), **add** it. |
| `clause_failed` | `ClauseFailure`: `clause_id`, `reason`, `retryable` | A clause that wasn't checked. `reason: "not_checked"` means time or the token budget ran out (the most important clauses are checked first); other reasons are errors. |
| `done` | `Summary`: `top_asks` (up to 3), `ask_list`, `contract_issues`, `missing_protections`, `good_news`, `matches_count`, `skipped_pages`, `versions` | Last event of a full check |

**Order** for a full check: `document`, then `contract_map`, then `progress`, `clause_result` and `clause_failed` interleaved in the order clauses finish, any `clause_updated`, and finally `done`. `heartbeat` can appear anywhere.

**Clients must:**

- Key everything by `clause_id`. A later event for the same clause replaces the earlier one: a `clause_result` after a `clause_failed` means a retry succeeded, so drop the failure.
- Treat a stream that ends **without** `done` as a dropped connection (network, timeout or server error), not as a finished check. The web app offers to check the unfinished clauses again through `/api/v1/clause-evaluations`.
- Ignore event types they don't know. Every event carries `schema_version` (`"1"` today).

### A clause result

The fields an artist sees, and the rules behind them:

| Field | Meaning |
|---|---|
| `comparison` | `matches_standard`, `better_for_you`, `worse_for_you`, `not_in_standard`, `missing_from_contract` or `cannot_compare`. The web app shows these as **Typical** (`matches_standard`, `better_for_you`), **Unusual** (`not_in_standard`), **Worth inquiry** (`worse_for_you`, `missing_from_contract`) and **Couldn't compare** (`cannot_compare`); see `frontend/src/lib/outcome.ts`. |
| `headline`, `what_it_says`, `what_it_means` | Mbiu's plain-language words, checked for reading level. Never show them in quote marks. |
| `original_text` | The contract's own words for this clause. Only this, `evidence_quote` and `standard_excerpt` are quotes. |
| `comparison_note` | One or two sentences on how the clause compares with the reference standard |
| `evidence`, `standard_excerpt`, `standard_template_id` | The reference standard the clause was compared with. `evidence[].source_title` names it. |
| `ask_them` | A neutral question the artist could ask, or `null` |
| `impact_inputs` | Figures quoted from the contract (royalty rate, gross or net basis, deductions), each with its `quote`. Never invent a figure that isn't quoted. |
| `linked_clauses` | Other clauses this one refers to or depends on |
| `provider`, `model_version` | Which AI answered. For support and evals, not for artists. |

`Summary.versions` records the `schema_version`, `prompt`, `model` and `corpus` behind the check. Include it in bug reports: it says exactly which prompt and reference corpus produced a result.

## Errors

A request refused before the stream starts returns JSON:

```json
{"code": "too_many_pages", "message": "This contract has more than 40 pages…"}
```

`message` is written for the artist and can be shown as it is.

| `code` | HTTP | Cause |
|---|---|---|
| `bot_check_failed` | 400 | Missing, invalid or reused Turnstile token |
| `invalid_file_type` | 400 | Not a PDF, an empty or broken PDF, or no file sent |
| `file_too_large` | 400 | Larger than `MAX_UPLOAD_MB` |
| `too_many_pages` | 400 | More pages than `MAX_PAGES` |
| `encrypted_pdf` | 400 | Password-protected PDF |
| `scanned_pdf` | 400 | No text layer (a scan or photo) |
| `invalid_request` | 400 | `/api/v1/clause-evaluations` body doesn't match the schema |
| `service_unavailable` | 503 or 500 | Reading the PDF took too long or too much memory, or an unexpected error. Safe to try again. |

`mostly_not_english` and `rate_limited` are defined in the schema for future use; the API doesn't return them yet. Pages that aren't in English are skipped and listed in `skipped_pages` instead.

Errors after the stream has started can't change the status code. They appear as `clause_failed` events, or the stream ends early without `done`.

## Time and cost limits

Each check has a deadline of 10 seconds plus 3 seconds per clause, capped at 300 seconds (`DEADLINE_PER_CLAUSE_S`, `DEADLINE_CAP_S`), and a token budget (`TOKEN_BUDGET_PER_CONTRACT`, default 400,000). Clauses are checked most important first, in batches (`BATCH_SIZE`, `LLM_CONCURRENCY`). Whatever the deadline or budget doesn't reach is sent as `clause_failed` with `reason: "not_checked"`.

## CORS

Only the origins in `CORS_ALLOWED_ORIGINS` may call the `POST` endpoints from a browser. Allowed methods: `POST, OPTIONS`; allowed headers: `Content-Type`, `traceparent`, `X-Requested-With`, `X-Turnstile-Token`. No cookies or credentials are used. `CORS_ALLOWED_ORIGINS` defaults to `http://localhost:3000` for local development; production sets it to the web app's address.

## Health checks

| Path | `200` | `503` |
|---|---|---|
| `/healthz` | The process answers | – |
| `/readyz` | `{"status": "ready"}`: the database answers and a reference corpus is active and loaded | `{"status": "not_ready", "failed": ["database"]}` or `["corpus"]` |

When `/readyz` fails, follow [runbooks/supabase-paused.md](runbooks/supabase-paused.md) or [runbooks/corpus-rollback.md](runbooks/corpus-rollback.md).

## Trying it locally

With the stack running (`just dev`) and Cloudflare's always-pass test keys in `.env`:

```bash
curl -N http://localhost:8000/api/v1/evaluations \
  -H "Origin: http://localhost:3000" \
  -F "file=@evals/datasets/pdfs/golden-combined-risks.pdf;type=application/pdf" \
  -F "turnstile_token=XXXX.DUMMY.TOKEN.XXXX"
```

Each line printed is one event.
