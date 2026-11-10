# 0004. Gemini call settings

**Status:** Accepted

## Context

Clause checks run on Google Gemini through the Interactions API (`backend/mbiu/llm/gemini.py`). Each contract has a deadline (10 seconds plus 3 per clause, capped at 300) and a token budget. Contract text must not be kept by the provider.

On 8 November 2026 uploads in production timed out. Measured on the 11-page sample contract, the whole-contract check took 95.8 seconds with Gemini's default (high) thinking and 6.5 seconds with low thinking, with the same result. The hidden thinking also counted as output tokens and made up most of the bill.

## Decision

- `store=False` on every call.
- `thinking_level` comes from `GEMINI_THINKING_LEVEL`, default `low`. `medium` is the next step if quality drops; `minimal` broke the structured answer in testing.
- The SDK's own retries are off (`HttpRetryOptions(attempts=0)`); Mbiu retries once itself, only for rate limits, timeouts and server errors, inside the deadline. A circuit breaker stops calls for 60 seconds after 5 outage errors in a row.
- OpenAI is a backup only, off unless `FAILOVER_ENABLED=true`, and also called with storage off.

## Consequences

- Changing the thinking level, model or retries changes speed, cost and quality together. Measure on the sample contracts before and after.
- Whether Google may use the text depends on the account's tier. Production needs a paid key before real artists' contracts are checked; see [data-transfers.md](../data-transfers.md).
