import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ClauseCard } from "./ClauseCard";
import type { ClauseResult } from "@/lib/api/generated/types.gen";

const mockWorseResult: ClauseResult = {
  clause_id: "c-royalties",
  status: "evaluated",
  comparison: "worse_for_you",
  headline: "You could earn very little from your songs for years",
  what_it_says: "Artist receives 12% royalty on Net Receipts after all expenses.",
  what_it_means: "Because deductions are uncapped, production and marketing overhead can wipe out your payout.",
  original_text: "Company shall pay Artist a royalty of 12% of Net Receipts, defined after deduction of all recording costs, marketing, distribution fees, legal fees, packaging charges, and general overhead.",
  pages: [4],
  linked_clauses: ["c-suspension"],
  evidence: [],
  evidence_ids: [],
  comparison_note: "12% Net vs standard 18-25% with capped deductions.",
  evidence_quote: null,
  standard_excerpt: "Standard indie royalty is 18-25% on net receipts with capped deductions.",
  standard_template_id: "std-rec-kenya-2024",
  ask_them: "Can we cap allowable deductions at 20% of gross receipts?",
  impact_inputs: {
    royalty_rate_percent: { quote: "12%", value: 12 },
    money_basis: { quote: "Net Receipts", value: "net" },
    deductions: [
      { quote: "recording costs", value: "recording costs" },
      { quote: "marketing", value: "marketing" },
      { quote: "general overhead", value: "general overhead" },
    ],
  },
  provider: "gemini",
  model_version: "gemini-3.8-flash",
};

const mockBetterResult: ClauseResult = {
  clause_id: "c-reversion",
  status: "evaluated",
  comparison: "better_for_you",
  headline: "Your master recordings revert back to you after 3 years",
  what_it_says: "All masters revert to Artist within 36 months of commercial release.",
  what_it_means: "You regain full ownership of your catalog faster than the standard 5-7 year term.",
  original_text: "Upon expiration of three (3) years following first commercial exploitation, all ownership rights revert fully to Artist.",
  pages: [2],
  linked_clauses: [],
  evidence: [],
  evidence_ids: [],
  comparison_note: null,
  evidence_quote: null,
  standard_excerpt: "Standard reversion term is 5 to 7 years.",
  standard_template_id: "std-rec-kenya-2024",
  ask_them: null,
  impact_inputs: null,
  provider: "gemini",
  model_version: "gemini-3.8-flash",
};

const render = (props: Partial<React.ComponentProps<typeof ClauseCard>> = {}) =>
  renderToStaticMarkup(
    <ClauseCard result={mockWorseResult} clauseNumber="7.2" clauseHeading="Royalties" {...props} />,
  );

describe("ClauseCard", () => {
  it("leads with the clause name, the outcome and Mbiu's headline", () => {
    const html = render();
    expect(html).toContain("Clause 7.2 · Royalties");
    expect(html).toContain("Worth inquiry");
    expect(html).toMatch(/<h3[^>]*>You could earn very little from your songs for years<\/h3>/);
    expect(html).not.toContain(">c-royalties<");
  });

  it("explains why it matters and what usual contracts say, with the source", () => {
    const html = render();
    expect(html).toContain("Why it matters");
    expect(html).toContain("Because deductions are uncapped");
    expect(html).toContain("What usual contracts say");
    expect(html).toContain("12% Net vs standard 18-25% with capped deductions.");
    expect(html).toContain("Compared with: std-rec-kenya-2024");
  });

  it("puts Mbiu's summary under 'In simple words' without quote marks", () => {
    const html = render();
    expect(html).toContain("In simple words");
    expect(html).toContain("Artist receives 12% royalty on Net Receipts after all expenses.");
    expect(html).not.toContain("“Artist receives");
  });

  it("quotes the contract's own words under 'See the exact words'", () => {
    const html = render();
    expect(html).toContain("See the exact words");
    expect(html).toContain("“Company shall pay Artist a royalty of 12%");
  });

  it("never prints a raw template form", () => {
    const html = render({
      result: {
        ...mockWorseResult,
        standard_excerpt:
          "## RECORDING/PRODUCER AGREEMENT This license agreement is made this …………….. day of ………20…. between",
      },
    });
    expect(html).not.toContain("##");
    expect(html).not.toContain("……");
  });

  it("offers the question to ask with copy and WhatsApp, without quote marks", () => {
    const html = render();
    expect(html).toContain("Ask them this");
    expect(html).toContain("Can we cap allowable deductions at 20% of gross receipts?");
    expect(html).not.toContain("“Can we cap");
    expect(html).toContain("https://wa.me/?text=");
    expect(html).toContain(encodeURIComponent(mockWorseResult.ask_them!));
    expect(html).toContain("Copy");
  });

  it("shows no question box without a question", () => {
    expect(render({ result: mockBetterResult })).not.toContain("Ask them this");
  });

  it("shows three linked clauses and a count for the rest", () => {
    const links = ["1.3", "1.5", "5.1", "6.1", "22"].map((n) => ({ clauseId: `c-${n}`, label: n }));
    const html = render({ linkedClauses: links, onSelectClause: () => {} });
    expect(html).toContain("Linked:");
    expect(html).toContain(">1.3<");
    expect(html).toContain(">5.1<");
    expect(html).toContain("+2");
  });

  it("shows the shillings steps when the contract quotes figures", () => {
    const html = render();
    expect(html).toContain('data-testid="shillings-calculator"');
    expect(html).toContain("If the label receives");
  });

  it("draws no calculator box when nothing is quoted as a number", () => {
    const html = render({
      result: {
        ...mockWorseResult,
        impact_inputs: { royalty_rate_percent: null, money_basis: null, deductions: [{ quote: "fees", value: "fees" }] },
      },
    });
    expect(html).not.toContain('data-testid="shillings-calculator"');
  });

  it("links to the clause's page in the contract", () => {
    const html = render({ onJumpToPdfClause: () => {} });
    expect(html).toContain("View on page 4");
  });

  it("keeps the small print short and read aloud available", () => {
    const html = render();
    expect(html).toContain("Not legal advice.");
    expect(html).toContain("Read aloud");
  });

  it("says when the whole-contract check changed the result", () => {
    expect(render({ isUpdated: true })).toContain("Result updated based on whole-contract check");
    expect(render()).not.toContain("Result updated");
  });
});
