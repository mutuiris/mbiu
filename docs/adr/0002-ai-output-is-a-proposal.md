# 0002. AI output is a proposal, checked in code

**Status:** Accepted

## Context

A language model can misquote a contract, invent a number, use legal jargon or slip into legal advice. Artists will act on what Mbiu shows them, so a confident but wrong card is worse than no card.

## Decision

Every clause result from the model is a proposal. Before it reaches the artist it must pass every rule in `backend/mbiu/evaluation/verify.py`:

| Rule | Checks that |
|---|---|
| `quotes_are_exact` | Quotes match the contract or the reference text word for word |
| `ids_are_real` | Every clause and evidence id was actually sent |
| `numbers_are_grounded` | Every number appears in the text that was sent |
| `no_legal_conclusions` | No "illegal", "unenforceable", "safe", "you should sign" and the like, unless the contract itself uses the word |
| `plain_language` | Reading level at or below `MAX_READING_GRADE` (default 9), jargon explained |
| `fits_a_phone` | The card is short enough to read on a phone |
| `usable_question` | The question to ask is a real, neutral question |
| `impact_inputs_grounded` | Money figures for the calculator are quoted from the contract |
| `money_is_comparable` | Money is compared on the same basis (gross with gross, net with net) |

When a proposal fails, the model is shown the failed checks and asked once to fix them. If it still fails, none of its wording is used: the clause is sent as "Couldn't compare" ("Mbiu couldn't verify this comparison") rather than shown wrong.

## Consequences

- Some clauses end up "Couldn't compare" even when the model's answer was nearly right.
- Prompt changes must keep passing these rules and the golden set (`evals/`). A prompt that adds examples, fixed outcomes or extra context needs an eval showing it helps before it ships.
- The frontend must not add claims of its own that these rules would reject (for example "no major impact" or an invented royalty rate).
