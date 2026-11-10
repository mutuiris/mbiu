# Mbiu web app

The Next.js app artists use: upload a contract, watch the results stream in, read the report and download it as a PDF. Setup and deployment are in the [root README](../README.md); the API it talks to is described in [docs/api.md](../docs/api.md).

## Layout

```
src/
├── app/                  routes: / (upload and results), /results (sample preview), /team, /privacy, /terms;
│                         layout.tsx holds the site metadata and share card
├── components/
│   ├── results/          the report: ReportHeader, QuestionsToAsk, ContractIssuesPanel, ClauseSection,
│   │                     ClauseCard, ShillingsCalculator, SummaryCard; ui.tsx has the shared building blocks
│   ├── report-pdf/       the downloadable PDF, built in the browser
│   ├── viewer/           the contract viewer (side panel on wide screens, bottom sheet on phones)
│   └── …                 Navbar, Footer, Turnstile, FileDropzone
└── lib/
    ├── api/              generated API types and the NDJSON stream client (stream.ts)
    ├── report.ts         clause names, merged questions, grouping for the report
    ├── impact.ts         the shillings calculator's maths (quoted figures only)
    ├── outcome.ts        the four labels artists see
    ├── keep-tab.ts       "Keep results on this phone for 1 hour"
    └── browser-polyfills.ts  JavaScript Safari lacks; must load before pdf.js
```

Tests sit next to the code they test (`*.test.ts`, `*.test.tsx`).

## Commands

From `frontend/`, with Node 24 and pnpm:

```bash
pnpm dev            # http://localhost:3000
pnpm test           # vitest
pnpm lint
pnpm typecheck
pnpm build
pnpm generate:api   # regenerate API types; or `just types` from the root after a backend model change
```

New dependencies must be at least 14 days old; pnpm enforces this (`minimumReleaseAge` in `pnpm-workspace.yaml`).

## Rules the UI keeps

- Labels are exactly **Typical**, **Unusual**, **Worth inquiry** and **Couldn't compare** ([decision 0003](../docs/adr/0003-four-neutral-labels.md)).
- Quote marks only around the contract's own words, never around Mbiu's summaries.
- Never show internal clause ids; use `readableClauseName` and `displayNumber` from `lib/report.ts`.
- Never invent a figure in the calculator: only percentages and rates the contract quotes.
- Nothing leaves the device except the upload itself ([decision 0001](../docs/adr/0001-never-store-contracts.md)).
- Tap targets at least 44 px tall, dark mode supported, and check pages in Safari as well as Chrome.
