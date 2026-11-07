import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { EvaluationReportModal } from "./EvaluationReportModal";
import type {
  ClauseResult,
  DocumentPayload,
  Summary,
  ContractMapPayload,
} from "@/lib/api/generated/types.gen";

const mockClauses: ClauseResult[] = [
  {
    clause_id: "c-royalty",
    status: "evaluated",
    comparison: "worse_for_you",
    headline: "You receive only 12% royalties after uncapped deductions",
    what_it_says: "Artist receives 12% royalty on Net Receipts after all recording and marketing expenses.",
    what_it_means: "Because deductions are uncapped, production costs could eliminate your payout entirely.",
    original_text: "Artist receives 12% royalty on Net Receipts after all recording and marketing expenses.",
    pages: [3],
    linked_clauses: [],
    evidence: [
      {
        evidence_id: "ev-1",
        template_id: "std-rec-kenya-2024",
        source_title: "KECOBO Standard Recording Agreement 2024",
        jurisdiction: "KE",
        excerpt: "Standard indie royalty is 18-25% on net receipts with capped deductions.",
      },
    ],
    evidence_ids: ["ev-1"],
    comparison_note: "12% Net vs standard 18-25% with capped deductions.",
    evidence_quote: null,
    standard_excerpt: "Standard indie royalty is 18-25% on net receipts with capped deductions.",
    standard_template_id: "std-rec-kenya-2024",
    ask_them: "Can we cap allowable deductions at 20% of gross receipts?",
    impact_inputs: null,
    provider: "gemini",
    model_version: "gemini-3.8-flash",
  },
  {
    clause_id: "c-term",
    status: "evaluated",
    comparison: "matches_standard",
    headline: "The contract runs for an initial term of 2 years",
    what_it_says: "This Agreement shall commence on the Effective Date and continue for two (2) years.",
    what_it_means: "A two-year term is standard for initial recording commitments.",
    original_text: "This Agreement shall commence on the Effective Date and continue for two (2) years.",
    pages: [1],
    linked_clauses: [],
    evidence: [],
    evidence_ids: [],
    comparison_note: "Matches standard 2-year term.",
    evidence_quote: null,
    standard_excerpt: null,
    standard_template_id: null,
    ask_them: null,
    impact_inputs: null,
    provider: "gemini",
    model_version: "gemini-3.8-flash",
  },
];

const mockDocument: DocumentPayload = {
  page_count: 5,
  sections: [],
  skipped_pages: [],
  clauses: [
    {
      clause_id: "c-term",
      number: "1.1",
      heading: "Term",
      pages: [1],
      section_id: "sec-1",
      start: 0,
      end: 100,
      text: "This Agreement shall commence on the Effective Date and continue for two (2) years.",
    },
    {
      clause_id: "c-royalty",
      number: "4.2",
      heading: "Royalties",
      pages: [3],
      section_id: "sec-2",
      start: 500,
      end: 650,
      text: "Artist receives 12% royalty on Net Receipts after all recording and marketing expenses.",
    },
  ],
};

const mockSummary: Summary = {
  matches_count: 1,
  contract_issues: [],
  good_news: [],
  missing_protections: [
    {
      template_id: "std-rec-kenya-2024",
      title: "Audit Rights",
      excerpt: "Artist shall have the right to inspect books once per calendar year.",
      ask_them: "Can we include standard annual audit rights for royalty statements?",
    },
  ],
  skipped_pages: [],
  top_asks: [
    {
      clause_id: "c-royalty",
      question: "Can we cap allowable deductions at 20% of gross receipts?",
    },
  ],
  ask_list: [
    {
      clause_id: "c-royalty",
      question: "Can we cap allowable deductions at 20% of gross receipts?",
    },
  ],
  versions: {
    schema_version: "1.0",
    prompt: "v1.2",
    model: "gemini-3.8-flash",
    corpus: "KECOBO-Indie-2024",
  },
};

const mockContractMap: ContractMapPayload = {
  contract_type: "recording",
  links: [],
  issues: [
    {
      kind: "conflict",
      explanation: "Clause 1.1 sets a 2-year term, while clause 16.3 grants rights in perpetuity.",
      clause_ids: ["c-term", "c-royalty"],
      pages: [1, 3],
      quotes: ["2-year term", "rights in perpetuity"],
    },
  ],
};

describe("EvaluationReportModal Component", () => {
  it("does not render when isOpen is false", () => {
    const html = renderToStaticMarkup(
      <EvaluationReportModal
        isOpen={false}
        onClose={vi.fn()}
        document={mockDocument}
        allResults={mockClauses}
        highImpactResults={mockClauses}
        contractMap={mockContractMap}
        summary={mockSummary}
        clauseLookup={new Map()}
      />,
    );
    expect(html).toBe("");
  });

  it("renders all sections in strict black-and-white report format", () => {
    const clauseLookup = new Map([
      ["c-term", { number: "1.1", heading: "Term", pages: [1] }],
      ["c-royalty", { number: "4.2", heading: "Royalties", pages: [3] }],
    ]);

    const html = renderToStaticMarkup(
      <EvaluationReportModal
        isOpen={true}
        onClose={vi.fn()}
        document={mockDocument}
        allResults={mockClauses}
        highImpactResults={mockClauses}
        contractMap={mockContractMap}
        summary={mockSummary}
        clauseLookup={clauseLookup}
      />,
    );

    // 1. Cover / Header with title, date, page/clause counts, and disclaimer
    expect(html).toContain("MBIU CONTRACT EVALUATION REPORT");
    expect(html).toContain("5 pages · 2 total clauses");
    expect(html).toContain("IMPORTANT NOTICE:");
    expect(html).toContain("does not judge whether any clause is lawful or enforceable, and it is not legal advice");

    // 2. How to read this report with the 4 neutral labels
    expect(html).toContain("1. How to Read This Report");
    expect(html).toContain("[TYPICAL]");
    expect(html).toContain("[UNUSUAL]");
    expect(html).toContain("[WORTH ASKING ABOUT]");
    expect(html).toContain("[COULDN&#x27;T COMPARE]");

    // 3. Executive summary dashboard
    expect(html).toContain("2. Executive Summary Dashboard");
    expect(html).toContain("Contract-wide contradictions or overrides:");
    expect(html).toContain("Missing standard protections (reverse check):");
    expect(html).toContain("Priority Questions to Ask Counterparty:");

    // 4. Contract-wide issues (if present)
    expect(html).toContain("3. Contract-Wide Issues (Overrides &amp; Conflicts)");
    expect(html).toContain("Clause 1.1 sets a 2-year term, while clause 16.3 grants rights in perpetuity.");

    // 5. Breakdown of high-impact clauses
    expect(html).toContain("4. Breakdown of High-Impact Evaluated Clauses");
    expect(html).toContain("What your contract says:");
    expect(html).toContain("Artist receives 12% royalty on Net Receipts after all recording and marketing expenses.");
    expect(html).toContain("In plain language:");
    expect(html).toContain("You receive only 12% royalties after uncapped deductions");
    expect(html).toContain("Why this may matter to you:");
    expect(html).toContain("Because deductions are uncapped, production costs could eliminate your payout entirely.");
    expect(html).toContain("How it compares:");
    expect(html).toContain("12% Net vs standard 18-25% with capped deductions.");
    expect(html).toContain("Questions you could ask:");
    expect(html).toContain("Can we cap allowable deductions at 20% of gross receipts?");

    // 6. Missing standard protections
    expect(html).toContain("5. Missing Protections (“Not Found in Your Contract”)");
    expect(html).toContain("Audit Rights");
    expect(html).toContain("Can we include standard annual audit rights for royalty statements?");

    // 7. Numbered negotiation checklist with checkable boxes and writing lines
    expect(html).toContain("6. Numbered Negotiation Checklist");
    expect(html).toContain("checkbox-square");
    expect(html).toContain("Notes: __________________________________________________________________________________");
    expect(html).toContain("Agreed: _________________________________________________ Date: _______________ Initials: _____");

    // 8. Reference standards cited
    expect(html).toContain("7. Reference Standards Cited");
    expect(html).toContain("KECOBO Standard Recording Agreement 2024");

    // 9. Running footer
    expect(html).toContain("Mbiu Contract Evaluation Report");
    expect(html).toContain("Not Legal Advice");
  });
});
