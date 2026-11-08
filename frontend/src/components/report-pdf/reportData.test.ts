import { describe, expect, it } from "vitest";

import type { ClauseResult, DocumentPayload, Summary } from "@/lib/api/generated/types.gen";

import { reportData } from "./download";

const result: ClauseResult = {
  clause_id: "c-18",
  status: "evaluated",
  comparison: "not_in_standard",
  headline: "You don't get paid for 15% of your streams and sales.",
  what_it_says: "The label treats 15% of what you sell as free.",
  what_it_means: "No royalty is paid on that 15%.",
  original_text: "Free Goods Allowance means fifteen percent (15%) of all units.",
  pages: [2],
  linked_clauses: [],
  evidence: [],
  evidence_ids: [],
  comparison_note: "Usual contracts don't take this cut from streams.",
  evidence_quote: null,
  standard_excerpt: null,
  standard_template_id: "kecobo-recording",
  ask_them: "Can you remove the 15% free goods cut on streams?",
  impact_inputs: null,
  provider: "gemini",
  model_version: "gemini-3.8-flash",
};
const document: DocumentPayload = {
  page_count: 11,
  sections: [],
  skipped_pages: [],
  clauses: [
    { clause_id: "c-18", number: "1.8", heading: "Free goods", text: "Free Goods…", pages: [2], section_id: "main", start: 0, end: 10 },
  ] as DocumentPayload["clauses"],
};
const summary: Summary = {
  top_asks: [
    { clause_id: "c-18", question: "Could we remove the 15% free goods deduction on digital streams, downloads, and ringtones?" },
    { clause_id: "c-18", question: "Could we remove the Free Goods Allowance of fifteen percent (15%)?" },
  ],
  ask_list: [],
  contract_issues: [],
  good_news: [],
  matches_count: 0,
  missing_protections: [],
  skipped_pages: [],
  versions: { schema_version: "1", prompt: "compare_v1", model: "gemini-3.8-flash", corpus: "20261106" },
};
const base = {
  document,
  results: [result],
  cards: [result],
  contractMap: null,
  summary,
  clauseLookup: new Map([["c-18", { number: "1.8", heading: "Free goods", pages: [2] }]]),
  isStreaming: false,
  today: new Date("2026-11-08T10:00:00Z"),
};

describe("reportData", () => {
  it("names the file by date and says the check is complete", () => {
    const data = reportData(base);
    expect(data.fileName).toBe("mbiu-report-2026-11-08.pdf");
    expect(data.status).toBe("Completed (1 clause evaluated)");
    expect(data.date).toBe("8 November 2026");
  });

  it("dates the file by Kenyan time, not UTC", () => {
    const data = reportData({ ...base, today: new Date("2026-11-08T22:00:00Z") });
    expect(data.fileName).toBe("mbiu-report-2026-11-09.pdf");
    expect(data.date).toBe("9 November 2026");
  });

  it("works while checking is still running, before any summary", () => {
    const data = reportData({ ...base, summary: null, isStreaming: true });
    expect(data.status).toBe("In progress (1 of 1 checked)");
    expect(data.questions).toEqual([]);
  });

  it("never shows a slug clause number next to a question", () => {
    const data = reportData({ ...base, clauseLookup: new Map([["c-18", { number: "1_2", heading: "Free goods", pages: [2] }]]) });
    expect(JSON.stringify(data.questions)).not.toContain("1_2");
  });

  it("merges repeated questions", () => {
    expect(reportData(base).questions).toHaveLength(1);
  });

  it("uses the approved outcome labels", () => {
    expect(reportData(base).legend.map((l) => l.label)).toEqual([
      "[TYPICAL]",
      "[UNUSUAL]",
      "[WORTH INQUIRY]",
      "[COULDN'T COMPARE]",
    ]);
  });

  it("keeps Mbiu's summary unquoted and the contract's words quoted", () => {
    const clause = reportData(base).clauses[0];
    expect(clause.inSimpleWords).toBe("The label treats 15% of what you sell as free.");
    expect(clause.exactWords).toBe("“Free Goods Allowance means fifteen percent (15%) of all units.”");
    expect(clause.title).toBe("Clause 1.8 · Free goods");
    expect(clause.label).toBe("[UNUSUAL]");
  });

  it("never fills 'what usual contracts say' with raw template text", () => {
    const data = reportData({
      ...base,
      cards: [{ ...result, comparison_note: null, standard_excerpt: "## RECORDING AGREEMENT made this …… day of ……" }],
    });
    expect(data.clauses[0].usual).toBeNull();
  });

  it("puts the model name only in the small print", () => {
    const { smallPrint, ...rest } = reportData(base);
    expect(smallPrint).toContain("gemini-3.8-flash");
    expect(JSON.stringify(rest)).not.toContain("gemini-3.8-flash");
  });
});
