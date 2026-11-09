import { renderToBuffer } from "@react-pdf/renderer";
import { describe, expect, it } from "vitest";

import { ReportDocument } from "./ReportDocument";
import type { ReportData } from "./download";

const data: ReportData = {
  fileName: "mbiu-report-2026-11-08.pdf",
  date: "8 November 2026",
  scope: "11 pages · 127 total clauses",
  status: "Completed (24 clauses evaluated)",
  reportId: "MBIU-2026-24C",
  legend: [{ label: "[UNUSUAL]", meaning: "Not usually in standard contracts." }],
  counts: [
    { label: "[TYPICAL]", count: 0 },
    { label: "[UNUSUAL]", count: 15 },
    { label: "[WORTH INQUIRY]", count: 0 },
    { label: "[COULDN'T COMPARE]", count: 9 },
  ],
  clashCount: 1,
  missingCount: 1,
  questions: [{ question: "Can you remove the 15% free goods cut on streams?", where: "Clause 1.8, page 2" }],
  clashes: [{ kind: "Two clauses disagree", explanation: "Different terms.", where: "Clause 4.4 and Clause 7.4", quotes: ["“10 years”", "“5 years”"] }],
  clauses: [
    {
      title: "Clause 1.8 · Free goods",
      label: "[UNUSUAL]",
      pages: "2",
      headline: "You don't get paid for 15% of your streams.",
      inSimpleWords: "The label treats 15% of what you sell as free.",
      whyItMatters: "No royalty is paid on that 15%.",
      usual: "Usual contracts don't take this cut from streams.",
      ask: "Can you remove it?",
      sources: "KECOBO recording agreement",
      exactWords: "“Free Goods Allowance means fifteen percent (15%).”",
    },
  ],
  missing: [{ title: "Audit", ask: "Can I check your accounts once a year?" }],
  checklist: ["Can you remove it?"],
  smallPrint: "Made by Mbiu on the artist's own device.",
};

describe("ReportDocument", () => {
  it("renders a real PDF", async () => {
    const buffer = await renderToBuffer(<ReportDocument data={data} />);
    expect(buffer.subarray(0, 5).toString()).toBe("%PDF-");
    expect(buffer.length).toBeGreaterThan(2000);
  }, 30_000);

  it("renders a long report across many pages", async () => {
    const long: ReportData = {
      ...data,
      clashes: Array.from({ length: 5 }, (_, i) => ({ ...data.clashes[0], explanation: `Clash ${i}. `.repeat(20) })),
      clauses: Array.from({ length: 24 }, (_, i) => ({ ...data.clauses[0], title: `Clause ${i}`, whyItMatters: "Why. ".repeat(60) })),
      checklist: Array.from({ length: 30 }, (_, i) => `Question ${i}: can you change this clause so it is fair to me?`),
    };
    const buffer = await renderToBuffer(<ReportDocument data={long} />);
    expect(buffer.subarray(0, 5).toString()).toBe("%PDF-");
  }, 60_000);
});
