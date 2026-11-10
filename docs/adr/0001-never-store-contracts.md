# 0001. Never store contracts

**Status:** Accepted

## Context

Artists upload unsigned contracts that name them, their fees and their business partners. A leak would harm the people Mbiu exists to help, and storing contracts would bring data-protection duties a small team can't carry.

## Decision

- The API reads the PDF in memory, checks it and lets it go when the stream ends. No contract, clause text, prompt or AI answer is written to the database, disk, object storage, logs, traces or analytics.
- Results live in the artist's browser tab. "Keep results on this phone for 1 hour" keeps them in `sessionStorage` for that tab only, cleared on close, after 60 minutes, or on request (`frontend/src/lib/keep-tab.ts`).
- The PDF report is built on the artist's device (`frontend/src/components/report-pdf/`) and never sent to a server.
- Clause text sent to an AI provider is sent with storage turned off (see [0004](0004-gemini-call-settings.md) and [data-transfers.md](../data-transfers.md)).

## Consequences

- Mbiu can't show past results, retrieve an old contract or delete one on request, because none exist.
- A dropped connection loses results unless the artist kept them; the web app offers to check unfinished clauses again.
- Every new feature, log line or monitoring tool must be checked against this rule. The privacy canary test (`backend/tests/test_privacy_canary.py`) guards the logs.
