# 0005. The bot check fails closed

**Status:** Accepted

## Context

Every contract check costs AI tokens. Without a bot check, a script could run up the bill or use Mbiu as a free AI service.

## Decision

- Both check endpoints require a Cloudflare Turnstile token, verified with Cloudflare on the server before any work starts (`backend/mbiu/security/turnstile.py`).
- If the token is missing, invalid, already used, or Cloudflare can't be reached, the request is refused (`bot_check_failed`). There is no way around it, including in the frontend.
- Tokens are single use: the web app gets a fresh one for every upload and every re-check.
- Only Cloudflare's public test keys appear in the repo, for local use and tests. The real secret lives in the host's secret store.

## Consequences

- If Turnstile is down, nobody can check a contract.
- The widget's allowed hostnames in Cloudflare must include every domain the web app runs on.
