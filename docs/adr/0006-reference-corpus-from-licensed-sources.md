# 0006. The reference corpus comes only from licensed public sources

**Status:** Accepted

## Context

Mbiu tells artists how a clause compares with standard contracts. Those standards must be real documents Mbiu is allowed to reuse. Invented "standards", made-up legal claims or test data in the corpus would mislead artists while looking authoritative.

## Decision

- The corpus is built only by the corpus pipeline from the sources listed in `corpus/sources.yaml`. Each source needs a working URL, a confirmed licence and the body that reviewed it. See [corpus.md](../corpus.md).
- Every published corpus is a new version. Exactly one version is active; publishing activates the new one, and [the rollback runbook](../runbooks/corpus-rollback.md) restores an older one.
- The built-in synthetic templates (`backend/mbiu/corpus/synthetic.py`) are a fallback for tests and outages only. They must not claim to be official standards.
- Tests never run against a shared database: `backend/tests/conftest.py` refuses any database host that isn't local.

## Consequences

- Coverage grows only as fast as licensed sources are found. Contract types with no source get few "Typical" results.
- On 8 November 2026 test data ended up as the active corpus in production, and every clause was compared with two fake recording-royalty lines. The local-database guard was added on 10 November so that can't happen again from a test run.
