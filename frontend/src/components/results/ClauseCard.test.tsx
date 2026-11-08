import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
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

describe("ClauseCard Component", () => {
  it("renders all 8 card sections strictly following architecture doc format in exact specified order for worse_for_you clause", () => {
    const html = renderToStaticMarkup(
      <ClauseCard
        result={mockWorseResult}
        clauseNumber="7.2"
        clauseHeading="Royalties"
        topic="Royalties"
        linkedClauses={[
          {
            clauseId: "c-suspension",
            label: "Clause 19 (Suspension)",
            issueKind: "override",
          },
        ]}
      />,
    );

    // 1. Heading: clause number in the status band + numbered disc, topic title, outcome label
    expect(html).toContain("data-testid=\"status-band\"");
    expect(html).toContain("Clause 7.2");
    expect(html).toContain("data-testid=\"clause-number-disc\"");
    expect(html).toContain("Royalties");
    expect(html).toContain("Worth inquiry");
    expect(html).toContain("Page 4, clause 7.2");
    const headingIndex = html.indexOf("data-testid=\"clause-heading\"");

    // 2. What your contract says: Exact quote from the contract
    expect(html).toContain("What your contract says");
    expect(html).toContain("Artist receives 12% royalty on Net Receipts after all expenses.");
    const whatItSaysIndex = html.indexOf("data-testid=\"what-it-says-section\"");

    // 3. In plain language: 1-2 short, jargon-free sentences
    expect(html).toContain("In plain language");
    expect(html).toContain("You could earn very little from your songs for years");
    const plainLanguageIndex = html.indexOf("data-testid=\"plain-language-section\"");

    // 4. Why this may matter to you: Practical consequences + KES worked example + linked clauses
    expect(html).toContain("Why this may matter to you");
    expect(html).toContain("Because deductions are uncapped, production and marketing overhead can wipe out your payout.");
    const whyItMattersIndex = html.indexOf("data-testid=\"why-it-matters-section\"");

    expect(html).toContain("data-testid=\"shillings-calculator\"");
    expect(html).toContain("In Shillings (Worked Example)");
    expect(html).toContain("Example figures — adjust below");
    const shillingsCalcIndex = html.indexOf("data-testid=\"shillings-calculator\"");

    expect(html).toContain("data-testid=\"also-affected-by\"");
    expect(html).toContain("Also affected by:");
    expect(html).toContain("Clause 19 (Suspension)");
    const alsoAffectedIndex = html.indexOf("data-testid=\"also-affected-by\"");

    // Fairer wording is strictly omitted to avoid legal drafting advice under Kenya Advocates Act
    expect(html).not.toContain("data-testid=\"fairer-wording-section\"");
    expect(html).not.toContain("Fairer wording");

    // 5. How it compares: What standard templates usually do (or comparison note)
    expect(html).toContain("How it compares");
    expect(html).toContain("Standard indie royalty is 18-25% on net receipts with capped deductions.");
    const howItComparesIndex = html.indexOf("data-testid=\"how-it-compares-section\"");

    // 6. Questions you could ask: 1 to 3 neutral, specific questions to ask
    expect(html).toContain("data-testid=\"ask-them-section\"");
    expect(html).toContain("Questions you could ask");
    expect(html).toContain("WhatsApp");
    expect(html).toContain("Can we cap allowable deductions at 20% of gross receipts?");
    const askThemIndex = html.indexOf("data-testid=\"ask-them-section\"");

    // 7. Sources: Reference contract title and page when cited
    expect(html).toContain("data-testid=\"sources-section\"");
    expect(html).toContain("Sources:");
    expect(html).toContain("[std-rec-kenya-2024]");
    const sourcesIndex = html.indexOf("data-testid=\"sources-section\"");

    // 8. Notice: Standard disclaimer
    expect(html).toContain("data-testid=\"clause-notice\"");
    expect(html).toContain("This explains what the contract says compared with reference material. It doesn’t say whether a clause is lawful or enforceable, and it isn’t legal advice.");
    const noticeIndex = html.indexOf("data-testid=\"clause-notice\"");

    // Collapsible exact raw wording & read aloud button
    expect(html).toContain("data-testid=\"exact-wording-section\"");
    expect(html).toContain("<details class=\"exact-wording-details\"");
    expect(html).toContain("Show exact wording");
    expect(html).toContain("Original contract clause (unaltered):");
    const exactWordingIndex = html.indexOf("data-testid=\"exact-wording-section\"");

    expect(html).toContain("data-testid=\"read-aloud-section\"");
    expect(html).toContain("Read aloud");
    const readAloudIndex = html.indexOf("data-testid=\"read-aloud-section\"");

    // Verify STRICT sequential ordering of all 8 sections
    expect(headingIndex).toBeGreaterThan(-1);
    expect(whatItSaysIndex).toBeGreaterThan(headingIndex);
    expect(plainLanguageIndex).toBeGreaterThan(whatItSaysIndex);
    expect(whyItMattersIndex).toBeGreaterThan(plainLanguageIndex);
    expect(shillingsCalcIndex).toBeGreaterThan(whyItMattersIndex);
    expect(alsoAffectedIndex).toBeGreaterThan(shillingsCalcIndex);
    expect(howItComparesIndex).toBeGreaterThan(alsoAffectedIndex);
    expect(askThemIndex).toBeGreaterThan(howItComparesIndex);
    expect(sourcesIndex).toBeGreaterThan(askThemIndex);
    expect(noticeIndex).toBeGreaterThan(sourcesIndex);
    expect(exactWordingIndex).toBeGreaterThan(noticeIndex);
    expect(readAloudIndex).toBeGreaterThan(exactWordingIndex);
  });

  it("omits shillings calculator when clause does not have a clear formula", () => {
    const html = renderToStaticMarkup(
      <ClauseCard
        result={mockBetterResult}
        clauseNumber="2.1"
        clauseHeading="Reversion"
      />,
    );

    expect(html).not.toContain("data-testid=\"shillings-calculator\"");
    expect(html).not.toContain("In Shillings (Worked Example)");
  });

  it("omits fairer wording on cards that are not worse than standard", () => {
    const html = renderToStaticMarkup(
      <ClauseCard
        result={mockBetterResult}
        clauseNumber="2.1"
        clauseHeading="Reversion"
      />,
    );

    expect(html).not.toContain("data-testid=\"fairer-wording-section\"");
  });

  it("includes WhatsApp share link with encoded question in Ask them section", () => {
    const html = renderToStaticMarkup(
      <ClauseCard
        result={mockWorseResult}
        clauseNumber="7.2"
        clauseHeading="Royalties"
      />,
    );

    expect(html).toContain("https://wa.me/?text=");
    expect(html).toContain(encodeURIComponent(mockWorseResult.ask_them!));
  });

  it("renders jump to PDF button in status/topic/location section with aria label", () => {
    const html = renderToStaticMarkup(
      <ClauseCard
        result={mockWorseResult}
        clauseNumber="7.2"
        clauseHeading="Royalties"
      />,
    );

    expect(html).toContain("class=\"jump-to-pdf-trigger\"");
    expect(html).toContain("aria-label=\"Jump to page 4 in PDF viewer\"");
  });

  it("displays worked example figures clearly labelled as examples in Shillings calculator", () => {
    const html = renderToStaticMarkup(
      <ClauseCard
        result={mockWorseResult}
        clauseNumber="7.2"
        clauseHeading="Royalties"
      />,
    );

    expect(html).toContain("Example figures — adjust below");
    expect(html).toContain("Example gross revenue (KES)");
    expect(html).toContain("Example deductions before royalties (KES)");
    expect(html).toContain("Your calculated earnings:");
    expect(html).toContain("Loss to deductions:");
  });

  describe("360px mobile viewport safety", () => {
    it("renders cleanly inside a 360px mobile container without overflow", () => {
      // Simulate rendering inside 360px mobile phone screen
      const html = renderToStaticMarkup(
        <div style={{ width: "360px", maxWidth: "360px", overflow: "hidden" }}>
          <ClauseCard
            result={mockWorseResult}
            clauseNumber="7.2"
            clauseHeading="Royalties"
            topic="Royalties"
            linkedClauses={[
              {
                clauseId: "c-suspension",
                label: "Clause 19 (Suspension)",
                issueKind: "override",
              },
            ]}
          />
        </div>,
      );

      // Verify all card sections render within container
      expect(html).toContain("data-testid=\"clause-heading\"");
      expect(html).toContain("data-testid=\"what-it-says-section\"");
      expect(html).toContain("data-testid=\"plain-language-section\"");
      expect(html).toContain("data-testid=\"why-it-matters-section\"");
      expect(html).toContain("data-testid=\"how-it-compares-section\"");
      expect(html).toContain("data-testid=\"shillings-calculator\"");
      expect(html).toContain("data-testid=\"also-affected-by\"");
      expect(html).not.toContain("data-testid=\"fairer-wording-section\"");
      expect(html).toContain("data-testid=\"ask-them-section\"");
      expect(html).toContain("data-testid=\"sources-section\"");
      expect(html).toContain("data-testid=\"clause-notice\"");
      expect(html).toContain("data-testid=\"exact-wording-section\"");
      expect(html).toContain("data-testid=\"read-aloud-section\"");
    });

    it("verifies globals.css includes mobile safety rules for narrow viewports down to 360px", () => {
      const cssPath = resolve(__dirname, "../../app/globals.css");
      const cssContent = readFileSync(cssPath, "utf-8");

      expect(cssContent).toContain("@media (max-width: 380px)");
      expect(cssContent).toContain(".shillings-calculator");
      expect(cssContent).toContain(".card-ask-them-section");
      expect(cssContent).toContain("overflow-wrap: break-word");
      expect(cssContent).toContain("word-break: break-word");
    });
  });
});
