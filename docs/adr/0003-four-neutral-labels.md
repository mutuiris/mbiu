# 0003. Four neutral labels, never "safe"

**Status:** Accepted

## Context

The model compares each clause with reference standards and returns one of six outcomes (`matches_standard`, `better_for_you`, `worse_for_you`, `not_in_standard`, `missing_from_contract`, `cannot_compare`). Six labels are too many to skim, and a green "safe" label would read as legal advice.

## Decision

Artists see four labels (`frontend/src/lib/outcome.ts`):

| Label | Outcomes |
|---|---|
| **Typical** | `matches_standard`, `better_for_you` |
| **Unusual** | `not_in_standard` |
| **Worth inquiry** | `worse_for_you`, `missing_from_contract` |
| **Couldn't compare** | `cannot_compare` |

There is no green and no "safe". Typical means common in the reference standards, not good for the artist. The PDF report uses the same four labels.

## Consequences

- "Typical" depends on the reference corpus. When the corpus doesn't cover a kind of contract, almost nothing can be Typical (see [0006](0006-reference-corpus-from-licensed-sources.md)).
- The API keeps all six outcomes, so the labels can change without a backend change.
