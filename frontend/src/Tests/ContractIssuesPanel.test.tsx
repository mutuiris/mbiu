import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ContractIssuesPanel } from "@/components/results/ContractIssuesPanel";
import { ClauseCard } from "@/components/results/ClauseCard";
import { parseNDJSONStream } from "@/lib/api/stream";
import type { ContractIssue, ClauseResult } from "@/lib/api/generated/types.gen";

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
  it("renders nothing when issues array is empty or undefined", () => {
    const markupEmpty = renderToStaticMarkup(<ContractIssuesPanel issues={[]} />);
    expect(markupEmpty).toBe("");

    // @ts-expect-error testing falsy issues prop
    const markupUndefined = renderToStaticMarkup(<ContractIssuesPanel issues={undefined} />);
    expect(markupUndefined).toBe("");
  });

  it("renders all contract-wide issues with counts, explanations, and disclaimer", () => {
    const html = renderToStaticMarkup(
      <ContractIssuesPanel issues={mockIssues} clauseLookup={mockClauseLookup} />
    );

    // Section container and header count
    expect(html).toContain('data-testid="contract-issues-panel"');
    expect(html).toContain("Contract-Wide Issues (2)");

    // Plain-language explanations
    expect(html).toContain(
      "Clause 19 claims to override all royalty rights granted in clause 7.2"
    );
    expect(html).toContain("Clause 3.1 states masters revert after 3 years");

    // Both badges present
    expect(html).toContain("Override Claim");
    expect(html).toContain("Contradiction / Conflict");

    // Impartial disclaimer (Mbiu reports override claims; never decides court application)
    expect(html).toContain(
      "Mbiu reports that one clause claims to override another; it never decides which a court would apply."
    );

    // Verbatim quotes in collapsible details
    expect(html).toContain("Artist shall receive 15% royalty on all net sales.");
    expect(html).toContain(
      "Notwithstanding clause 7.2 or any other provision, no royalties accrue during suspension."
    );
  });

  it('formats both clause locations in plain language ("Page 4, clause 7.2 and page 11, clause 19")', () => {
    const html = renderToStaticMarkup(
      <ContractIssuesPanel issues={[mockIssues[0]]} clauseLookup={mockClauseLookup} />
    );

    // Plain language location formatting
    expect(html).toContain("Page 4, clause 7.2");
    expect(html).toContain("Page 11, clause 19");
    expect(html).toContain('class="locations-separator"> and </span>');
  });

  it("handles fallback formatting when clause lookup has no metadata", () => {
    const issueWithoutMeta: ContractIssue = {
      clause_ids: ["raw-id-A", "raw-id-B"],
      pages: [2, 6],
      kind: "conflict",
      explanation: "Direct clause conflict.",
      quotes: ["quote 1", "quote 2"],
    };

    const html = renderToStaticMarkup(
      <ContractIssuesPanel issues={[issueWithoutMeta]} />
    );

    expect(html).toContain("Page 2, clause raw-id-A");
    expect(html).toContain("Page 2, clause raw-id-B");
  });

  it("triggers onSelectClause callback when clause location button is tapped", () => {
    const onSelectClause = vi.fn();

    // Render component pure function to inspect React elements
    const element = ContractIssuesPanel({
      issues: [mockIssues[0]],
      clauseLookup: mockClauseLookup,
      onSelectClause,
    });

    expect(element).not.toBeNull();
    const sectionChildren = React.Children.toArray((element as React.ReactElement<{ children: React.ReactNode }>).props.children);
    const issuesList = sectionChildren[1] as React.ReactElement<{ children: React.ReactNode }>;
    const issueArticles = React.Children.toArray(issuesList.props.children) as React.ReactElement<{ children: React.ReactNode }>[];
    const firstArticle = issueArticles[0];
    const articleChildren = React.Children.toArray(firstArticle.props.children);
    const metaDiv = articleChildren[0] as React.ReactElement<{ children: React.ReactNode }>;
    const metaChildren = React.Children.toArray(metaDiv.props.children);
    const locationsDiv = metaChildren[1] as React.ReactElement<{ children: React.ReactNode }>;
    const locationElements = React.Children.toArray(locationsDiv.props.children);

    const btn1 = locationElements[0] as React.ReactElement<{ onClick?: () => void }>;
    const btn2 = locationElements[2] as React.ReactElement<{ onClick?: () => void }>;

    btn1.props.onClick?.();
    expect(onSelectClause).toHaveBeenCalledWith("c-1");

    btn2.props.onClick?.();
    expect(onSelectClause).toHaveBeenCalledWith("c-4");
  });
});

describe("ClauseCard 'Also affected by' & clause_updated Notice", () => {
  it("renders 'Also affected by' links with kind badges on ClauseCard", () => {
    const onSelectClause = vi.fn();
    const linkedClauses = [
      {
        clauseId: "c-4",
        label: "Clause 19 (Suspension)",
        kind: "override",
      },
      {
        clauseId: "c-6",
        label: "Clause 22 (Notice)",
        kind: "explicit_ref",
      },
    ];

    const html = renderToStaticMarkup(
      <ClauseCard
        result={mockClauseResult}
        linkedClauses={linkedClauses}
        onSelectClause={onSelectClause}
      />
    );

    expect(html).toContain('data-testid="also-affected-by"');
    expect(html).toContain("Also affected by:");
    expect(html).toContain("Clause 19 (Suspension)");
    expect(html).toContain("Clause 22 (Notice)");
    expect(html).toContain("override");
  });

  it("renders subtle update notice when isUpdated is true", () => {
    const htmlUpdated = renderToStaticMarkup(
      <ClauseCard
        result={mockClauseResult}
        isUpdated={true}
      />
    );

    expect(htmlUpdated).toContain('data-testid="clause-updated-notice"');
    expect(htmlUpdated).toContain("Result updated based on whole-contract check");

    const htmlNotUpdated = renderToStaticMarkup(
      <ClauseCard
        result={mockClauseResult}
        isUpdated={false}
      />
    );

    expect(htmlNotUpdated).not.toContain('data-testid="clause-updated-notice"');
  });

  it("calls onSelectClause when an affected-by button is clicked", () => {
    const onSelectClause = vi.fn();
    const linkedClauses = [
      {
        clauseId: "c-4",
        label: "Clause 19 (Suspension)",
        kind: "override",
      },
    ];

    const element = ClauseCard({
      result: mockClauseResult,
      linkedClauses,
      onSelectClause,
    });

    const rootChildren = React.Children.toArray((element as React.ReactElement<{ children: React.ReactNode }>).props.children);
    const comparisonSection = rootChildren.find(
      (child) => React.isValidElement(child) && (child as React.ReactElement<{ className?: string }>).props.className === "card-comparison-section"
    ) as React.ReactElement<{ children: React.ReactNode }>;

    expect(comparisonSection).toBeDefined();
    const compChildren = React.Children.toArray(comparisonSection.props.children);
    const affectedDiv = compChildren.find(
      (child) => React.isValidElement(child) && (child as React.ReactElement<{ className?: string }>).props.className === "card-affected-by"
    ) as React.ReactElement<{ children: React.ReactNode }>;

    expect(affectedDiv).toBeDefined();
    const affectedChildren = React.Children.toArray(affectedDiv.props.children);
    const linksDiv = affectedChildren[1] as React.ReactElement<{ children: React.ReactNode }>;
    const linkBtn = React.Children.toArray(linksDiv.props.children)[0] as React.ReactElement<{ onClick?: () => void }>;

    linkBtn.props.onClick?.();
    expect(onSelectClause).toHaveBeenCalledWith("c-4");
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
