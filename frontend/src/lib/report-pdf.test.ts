import { describe, expect, it } from "vitest";
import {
  formatHowItComparesSummary,
  generateEvaluationReportPdf,
  isCleanShortExcerpt,
} from "./report-pdf";
import type {
  ClauseResult,
  ContractMapPayload,
  DocumentPayload,
  Summary,
} from "./api/generated/types.gen";

const mockResult: ClauseResult = {
  clause_id: "c-1",
  status: "evaluated",
  comparison: "worse_for_you",
  headline: "You receive 12% royalties after uncapped deductions",
  what_it_says: "Artist receives 12% of Net Receipts after all expenses.",
  what_it_means: "Uncapped deductions can reduce your take-home pay to zero.",
  original_text: "Artist receives 12% of Net Receipts after all expenses.",
  pages: [2],
  linked_clauses: [],
  evidence: [
    {
      evidence_id: "ev-1",
      template_id: "kecobo-2024",
      source_title: "KECOBO Standard Recording Agreement",
      jurisdiction: "KE",
      excerpt: "8. Notices Any notice under this agreement shall be given in writing... ## 10. Dispute resolution... IN WITNESS WHEREOF",
    },
  ],
  evidence_ids: ["ev-1"],
  comparison_note: null,
  evidence_quote: null,
  standard_excerpt:
    "8. Notices Any notice under this agreement shall be given in writing and shall be deemed to have been delivered if sent by post after ....... days ## 10. Dispute resolution IN WITNESS WHEREOF",
  standard_template_id: "kecobo-2024",
  ask_them: "Can we cap deductions at 20% of gross revenue?",
  impact_inputs: null,
  provider: "gemini",
  model_version: "gemini-3.8-flash",
};

const mockDocument: DocumentPayload = {
  page_count: 4,
  sections: [],
  skipped_pages: [],
  clauses: [
    {
      clause_id: "c-1",
      number: "4.1",
      heading: "Royalties",
      pages: [2],
      section_id: "main",
      start: 0,
      end: 60,
      text: "Artist receives 12% of Net Receipts after all expenses.",
    },
  ],
};

const mockSummary: Summary = {
  matches_count: 16,
  contract_issues: [],
  good_news: [],
  missing_protections: [
    {
      template_id: "KE-AUDIT",
      title: "Audit Rights",
      excerpt: "Artist may inspect books annually.",
      ask_them: "Can we add annual audit rights?",
    },
  ],
  skipped_pages: [],
  top_asks: [
    {
      clause_id: "c-1",
      question: "Can we cap deductions at 20% of gross revenue?",
    },
  ],
  ask_list: [],
  versions: {
    schema_version: "1",
    prompt: "compare_v1",
    model: "gemini-3.8-flash",
    corpus: "v1",
  },
};

const mockMap: ContractMapPayload = {
  contract_type: "recording",
  links: [],
  issues: [],
};

describe("report-pdf", () => {
  it("identifies raw multi-section template chunks vs short clean excerpts", () => {
    expect(
      isCleanShortExcerpt("Standard indie royalty is 18-25% on net receipts with capped deductions."),
    ).toBe(true);
    expect(isCleanShortExcerpt(mockResult.standard_excerpt)).toBe(false);
  });

  it("formats a plain-language comparison summary without dumping raw template boilerplate", () => {
    const summaryText = formatHowItComparesSummary(mockResult);
    expect(summaryText).toContain("Less favorable than reviewed standards");
    expect(summaryText).toContain("KECOBO Standard Recording Agreement");
    expect(summaryText).not.toContain("IN WITNESS WHEREOF");
    expect(summaryText).not.toContain("## 10. Dispute resolution");
  });

  it("generates a valid PDF 1.4 binary document with all report sections", () => {
    const bytes = generateEvaluationReportPdf({
      document: mockDocument,
      allResults: [mockResult],
      highImpactResults: [mockResult],
      contractMap: mockMap,
      summary: mockSummary,
      clauseLookup: new Map([["c-1", { number: "4.1", heading: "Royalties", pages: [2] }]]),
      isStreaming: false,
    });

    const text = new TextDecoder().decode(bytes);
    expect(text.startsWith("%PDF-1.4\n")).toBe(true);
    expect(text).toContain("MBIU CONTRACT EVALUATION REPORT");
    expect(text).toContain("Clause 4.1: Royalties");
    expect(text).toContain("Can we cap deductions at 20% of gross revenue?");
    expect(text).toContain("%%EOF");
  });
});

