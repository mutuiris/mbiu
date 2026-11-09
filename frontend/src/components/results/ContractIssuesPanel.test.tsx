import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ContractIssuesPanel } from "./ContractIssuesPanel";
import { parseNDJSONStream } from "../../lib/api/stream";
import type { ContractIssue, ClauseResult } from "../../lib/api/generated/types.gen";

function createStreamFromChunks(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

const mockIssues: ContractIssue[] = [
  {
    clause_ids: ["c-1", "c-4"],
    pages: [4, 11],
    kind: "override",
    explanation:
      "Clause 19 claims to override all royalty rights granted in clause 7.2 notwithstanding any other terms.",
    quotes: [
      "Artist shall receive 15% royalty on all net sales.",
      "Notwithstanding clause 7.2 or any other provision, no royalties accrue during suspension.",
    ],
  },
  {
    clause_ids: ["c-2", "c-5"],
    pages: [3, 8],
    kind: "conflict",
    explanation:
      "Clause 3.1 states masters revert after 3 years, but clause 14 states the company holds master rights in perpetuity.",
    quotes: [
      "Masters revert to Artist within 36 months.",
      "Company owns all right, title, and interest in perpetuity.",
    ],
  },
];

const mockClauseLookup = new Map([
  ["c-1", { number: "7.2", heading: "Royalties", pages: [4] }],
  ["c-4", { number: "19", heading: "Suspension", pages: [11] }],
  ["c-2", { number: "3.1", heading: "Reversion", pages: [3] }],
  ["c-5", { number: "14", heading: "Ownership", pages: [8] }],
]);

const mockClauseResult: ClauseResult = {
  clause_id: "c-1",
  status: "evaluated",
  comparison: "worse_for_you",
  headline: "Royalties can be cancelled during label suspension",
  what_it_says: "Artist shall receive 15% royalty on all net sales.",
  what_it_means: "Even though 15% is standard, clause 19 cuts off this royalty entirely.",
  original_text: "Artist shall receive 15% royalty on all net sales.",
  pages: [4],
  linked_clauses: ["c-4"],
  evidence: [],
  evidence_ids: [],
  comparison_note: "Subject to override in clause 19.",
  evidence_quote: null,
  standard_excerpt: "Standard terms protect accrued royalties.",
  standard_template_id: "std-rec-kenya-2024",
  ask_them: "Can we ensure royalties are protected during administrative suspension?",
  impact_inputs: null,
  provider: "gemini",
  model_version: "gemini-3.8-flash",
};

describe("ContractIssuesPanel", () => {
  const five: ContractIssue[] = Array.from({ length: 5 }, (_, i) => ({
    ...mockIssues[i % 2],
    explanation: `Issue number ${i + 1}.`,
  }));

  it("renders nothing when issues array is empty or undefined", () => {
    expect(renderToStaticMarkup(<ContractIssuesPanel issues={[]} />)).toBe("");
    // @ts-expect-error testing falsy issues prop
    expect(renderToStaticMarkup(<ContractIssuesPanel issues={undefined} />)).toBe("");
  });

  it("names clashes in plain words and says the disclaimer once", () => {
    const html = renderToStaticMarkup(<ContractIssuesPanel issues={mockIssues} clauseLookup={mockClauseLookup} />);
    expect(html).toContain('data-testid="contract-issues-panel"');
    expect(html).toContain("Clauses that clash");
    expect(html).toContain("One clause cancels another");
    expect(html).toContain("Two clauses disagree");
    expect(html).toContain("Clause 19 claims to override all royalty rights granted in clause 7.2");
    const disclaimer = "Mbiu shows where one clause claims to override another. It never decides which a court would apply.";
    expect(html.split(disclaimer)).toHaveLength(2);
    expect(html).not.toContain("Contract-Wide");
  });

  it("names both clauses for artists and offers to show them", () => {
    const html = renderToStaticMarkup(
      <ContractIssuesPanel issues={[mockIssues[0]]} clauseLookup={mockClauseLookup} onSelectClause={() => {}} />,
    );
    expect(html).toContain("Clause 7.2 · Royalties");
    expect(html).toContain("Clause 19 · Suspension");
    expect(html).toContain("See both");
    expect(html).toContain("See the exact words");
  });

  it("never shows internal clause ids", () => {
    const html = renderToStaticMarkup(
      <ContractIssuesPanel
        issues={[{ clause_ids: ["raw-id-A", "raw-id-B"], pages: [2, 6], kind: "conflict", explanation: "Direct clause conflict.", quotes: ["quote 1", "quote 2"] }]}
      />,
    );
    expect(html).not.toContain("raw-id-A");
    expect(html).toContain("Direct clause conflict.");
  });

  it("shows the first three of five and offers the rest", () => {
    const html = renderToStaticMarkup(<ContractIssuesPanel issues={five} clauseLookup={mockClauseLookup} />);
    expect(html).toContain("Issue number 3.");
    expect(html).not.toContain("Issue number 4.");
    expect(html).toContain("Show all 5");
  });

  it("drops the disclaimer the rules append to each explanation", () => {
    const html = renderToStaticMarkup(
      <ContractIssuesPanel
        issues={[
          {
            ...mockIssues[0],
            explanation:
              "Clause 6.2 claims to override clause 6.1. Mbiu reports that one clause claims to override another; it never decides which a court would apply.",
          },
        ]}
      />,
    );
    expect(html).toContain("Clause 6.2 claims to override clause 6.1.");
    expect(html).not.toContain("Mbiu reports that one clause");
  });

  it("offers no 'show all' for three or fewer", () => {
    expect(renderToStaticMarkup(<ContractIssuesPanel issues={mockIssues} />)).not.toContain("Show all");
  });
});


describe("Stream parsing for contract_map and clause_updated", () => {
  it("parses contract_map event from stream", async () => {
    const contractMapLine = JSON.stringify({
      type: "contract_map",
      schema_version: "1",
      payload: {
        contract_type: "recording_agreement",
        links: [
          {
            from_clause_id: "c-1",
            to_clause_id: "c-4",
            kind: "override",
          },
        ],
        issues: [
          {
            clause_ids: ["c-1", "c-4"],
            pages: [4, 11],
            kind: "override",
            explanation: "Clause 19 overrides clause 7.2.",
            quotes: ["Quote A", "Quote B"],
          },
        ],
      },
    }) + "\n";

    const stream = createStreamFromChunks([contractMapLine]);
    const events = [];
    for await (const event of parseNDJSONStream(stream)) {
      events.push(event);
    }

    expect(events.length).toBe(1);
    expect(events[0].type).toBe("contract_map");
    if (events[0].type === "contract_map") {
      expect(events[0].payload.issues.length).toBe(1);
      expect(events[0].payload.issues[0].clause_ids).toEqual(["c-1", "c-4"]);
    }
  });

  it("parses clause_updated event from stream", async () => {
    const clauseUpdatedLine = JSON.stringify({
      type: "clause_updated",
      schema_version: "1",
      payload: mockClauseResult,
    }) + "\n";

    const stream = createStreamFromChunks([clauseUpdatedLine]);
    const events = [];
    for await (const event of parseNDJSONStream(stream)) {
      events.push(event);
    }

    expect(events.length).toBe(1);
    expect(events[0].type).toBe("clause_updated");
    if (events[0].type === "clause_updated") {
      expect(events[0].payload.clause_id).toBe("c-1");
      expect(events[0].payload.headline).toBe(mockClauseResult.headline);
    }
  });
});

describe("Responsive design at 360px wide", () => {
  it("includes responsive rules for narrow viewports (<=400px down to 360px)", () => {
    const cssPath = resolve(process.cwd(), "src/app/globals.css");
    const cssContent = readFileSync(cssPath, "utf-8");

    // Check media query for mobile/360px viewports
    expect(cssContent).toContain("@media (max-width: 400px)");

    // Check responsive issues panel styling
    expect(cssContent).toContain(".contract-issues-panel");
    expect(cssContent).toContain(".issue-locations");
    expect(cssContent).toContain(".clause-location-btn");
    expect(cssContent).toContain(".card-updated-notice");
    expect(cssContent).toContain(".card-affected-by");

    // Check flex-wrap and word-break to ensure no overflow at 360px
    expect(cssContent).toContain("flex-wrap: wrap");
    expect(cssContent).toContain("word-break: break-word");
  });
});
