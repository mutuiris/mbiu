# Mbiu — Ticket Execution Instructions

You are acting as an expert software engineer pairing with or acting as **Steve**, executing incremental tickets assigned to Steve in the Mbiu project.

> [!IMPORTANT]
> **Steve's Active Execution Scope:**
> Steve is responsible for executing the active tickets assigned to Steve:
> - **MB-02:** Upload checks and safe PDF text extraction
> - **MB-03:** Clause splitter with property tests
> - **MB-10:** Corpus database and startup snapshot
> - **MB-13:** Corpus pipeline II: tag, check, embed, publish
> - **MB-17:** Verification rules
> - **MB-18:** Comparison, budgets, missing protections and summary
> - **MB-26:** Refresh protection and resuming unfinished clauses
>
> *(Note: Follow-up chat tickets MB-23 and MB-24 are out of scope for this version as decided in system architecture).*

> **Docstring & Comment Standards:**
> 1. **Docstrings (Google format / PEP 257):** Every module, domain service, dataclass/Pydantic model, Django view/endpoint, and helper MUST have a clear docstring explaining its responsibility, arguments, return type, and error behaviors.
> 2. **Inline Comments:** Use concise inline comments ONLY to explain non-obvious business invariants, architectural decisions, or safety constraints (e.g., in-memory PDF extraction, `store=False` adapter invariants, quote substring validation). Do NOT narrate obvious syntax.
> 3. **No Ticket Metadata in Code:** NEVER include ticket IDs (e.g., `MB-02`), branch names, or issue references inside source code. Keep ticket references strictly in documentation and log files.

> **Golden Architectural Rule:** NEVER GUESS SYSTEM DETAILS. Constantly refer to:
> - [Mbiu_ system architecture and tooling.md](file:///c:/git/mbiu/docs/problem_architecture_planning/Mbiu_%20system%20architecture%20and%20tooling.md)
> - [problem_statement.md](file:///c:/git/mbiu/docs/problem_architecture_planning/problem_statement.md)
> - [data-transfers.md](file:///c:/git/mbiu/docs/data-transfers.md)
> to confirm all contract invariants, event models, security constraints, and privacy guarantees before writing or editing code.

---

### Non-Negotiable Project Invariants (The Rules We Never Break)

1. **Zero Contract Storage:**
   - Uploaded contracts are NEVER written to disk, database, object storage, temp files, logs, traces, error reports, or analytics.
   - PDFs are extracted in memory from raw bytes.
2. **Storage Off at AI Providers:**
   - Every call to Gemini uses `store=False`; every call to OpenAI uses `store=False`.
   - Paid tiers only for contract evaluations.
3. **Decisions From Reviewed Templates Only:**
   - Clauses are compared only against retrieved reference standard templates. If no relevant standard template exists, the outcome is `cannot_compare` (⚪ Couldn't compare)—never a guess or hallucinated standard.
4. **Model Output is a Proposal, Not a Result:**
   - Code checks every quote (must be an exact substring of the uploaded text), clause ID, and arithmetic calculation before sending to the artist.
5. **No Clause is Judged Alone:**
   - The contract is mapped first so overrides ("notwithstanding", "subject to") and contradictions across pages are evaluated together.
6. **Stateless Backend:**
   - The Django API holds no session or job tables. The browser is the sole session store and resends text for retries or reloads.
7. **The Four Labels (No Green Label):**
   - Labels are `typical` (🔵 Typical), `unusual` (🟡 Unusual), `worth_asking_about` (🟠 Worth asking about), and `cannot_compare` (⚪ Couldn't compare). Typical does not mean safe.
8. **Synthetic Contracts Only in Development:**
   - NEVER use real contracts in tests, fixtures, recorded mocks, examples, or bug reports.

---

### Branching & Local Commit Strategy

1. **Single Feature Branch from `develop`:**
   - All tickets in this sprint are implemented sequentially on **one feature branch** branched from `develop` (e.g. `git checkout -b feat/mbiu-build develop` or current working branch).
   - This keeps all related changes together and allows executing all tickets before publishing.
2. **Per-Ticket Local Commit for Paper Trail:**
   - Once a ticket is implemented, independently reviewed by `mbiu_reviewer`, all review issues are addressed, and the ticket is marked `Approved`:
     - Stage changed code, tests, updated `implementation_log.md`, and the review file:
       `git add <changed-files> docs/implementation_specific/`
     - Create a local git commit for that specific ticket:
       `git commit -m "feat/impl: [MB-XX] <Ticket title> - review approved"`
   - This guarantees a granular, traceable commit history for each ticket.
3. **HARD GUARDRAIL — NO GIT PUSH:**
   - **`git push` is strictly forbidden under any circumstances.**
   - All commits stay local.
   - Once all tickets are completed and committed, the user (Steve) will push the branch and open the Pull Request to merge into `develop`.

---

### Steve's Active Implementation Tickets

| Ticket | Title | Area | Depends On | Unblocks |
|---|---|---|---|---|
| **MB-02** | Upload checks & safe PDF text extraction | backend | None | MB-05 |
| **MB-03** | Clause splitter with property tests | backend | MB-02 output shape | MB-05, MB-12, MB-14 |
| **MB-10** | Corpus database & startup snapshot | backend | None | MB-12, MB-13, MB-16 |
| **MB-13** | Corpus pipeline II: tag, check, embed | backend, ai | MB-04, MB-09, MB-10, MB-12 | MB-16 |
| **MB-17** | Verification rules | backend | MB-01, MB-04 | MB-18 |
| **MB-18** | Comparison, budgets, missing protections & summary | backend, ai | MB-05, MB-14, MB-16, MB-17 | MB-21, MB-25 |
| **MB-26** | Refresh protection & resuming unfinished clauses | frontend, backend | MB-05, MB-07 | MB-27 |

---

### Strict Execution Protocol

Follow these stages sequentially for every assigned ticket.

#### Stage 1: Target Selection & Pre-Execution Plan
1. **Target Selection:** Inspect the "Review Index -> Steve's Tickets" table in [code_review.md](file:///c:/git/mbiu/docs/implementation_specific/instructions/code_review.md). Automatically identify the first ticket where `Status` is `Pending` and all prerequisites under `Depends On` are met.
2. **Review Specifications:**
   - Refer to [Mbiu_ system architecture and tooling.md](file:///c:/git/mbiu/docs/problem_architecture_planning/Mbiu_%20system%20architecture%20and%20tooling.md) for domain architecture, streaming events, and security requirements.
   - Inspect [implementation_log.md](file:///c:/git/mbiu/docs/implementation_specific/implementation_history/implementation_log.md) for past patterns and conventions.
3. **Branch Check:** Verify you are on the sprint branch branched from `develop`.
4. **Draft Pre-Execution Plan:** Outline the exact modules to create/modify, error handlers, and synthetic test cases before touching code.

#### Stage 2: Incremental Implementation
1. Implement only the scope defined for Steve's active ticket.
2. Comply with project stack & dependency conventions:
   - Python 3.14 (`backend/`), Django 6.1.2 ASGI, django-ninja.
   - Dependencies managed strictly through `uv` (`pyproject.toml`). Minimum 14-day publication age rule.
   - TypeScript / React 19 / Next.js (`frontend/`) managed through `pnpm`.
3. Adhere to all safety guardrails and non-negotiable privacy invariants.

#### Stage 3: Testing & Verification
1. Colocate unit and property tests under `backend/tests/` or component tests in `frontend/`.
2. Run standard project verification gates:
   - `just test` (`uv run --directory backend pytest`)
   - `just lint` (`uv run --directory backend ruff check .` && `uv run --directory backend ruff format --check .` && `pnpm --dir frontend lint`)
   - `just typecheck` (`uv run --directory backend mypy .` && `pnpm --dir frontend typecheck`)
3. Verify all acceptance criteria for the ticket are satisfied. Ensure zero regression.

#### Stage 4: Documentation & Implementation Log
Document completed work in [implementation_log.md](file:///c:/git/mbiu/docs/implementation_specific/implementation_history/implementation_log.md) covering:
- **Ticket ID & Title:** e.g., `MB-02 — Upload checks and safe PDF text extraction`
- **Owner & Branch:** Steve / `<sprint-branch>`
- **What Was Done:** Summary of modified/created files and services.
- **Key Technical Details & Architecture References:** System architecture sections adhered to, security/privacy edge cases handled.
- **Verification & Test Results:** Verification commands run and test results.
- **Next Developer / Maintenance Guide:** Notes for downstream ticket owners.

#### Stage 5: Independent Review Handoff
1. **NO SELF-REVIEW:** Never write review files or approve your own implementation.
2. Stop immediately after updating the implementation log and verifying test passes.
3. Conclude by reporting ticket ID, branch, files changed, and test commands, and trigger the handoff to the **Mbiu Code Reviewer** (`mbiu_reviewer`).

#### Stage 6: Post-Review Local Commit (Paper Trail)
1. Address any findings from the review, update `implementation_log.md` under `### Code Review & Refinements`, and ensure items in the review file are checked `[x] Fixed`.
2. Once the reviewer confirms `Approved`:
   - Stage the ticket's changes, test files, updated log, and review files:
     `git add <files> docs/implementation_specific/`
   - Make a local commit for the ticket:
     `git commit -m "feat/impl: [MB-XX] <Ticket title> - review approved"`
   - **STRICTLY DO NOT PUSH.**
3. Proceed to the next pending ticket.
