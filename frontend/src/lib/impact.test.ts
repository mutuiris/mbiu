import { describe, expect, it } from "vitest";
import {
  hasClearFormula,
  isHighImpactClause,
} from "./impact";
import type { ClauseResult, ImpactInputs } from "./api/generated/types.gen";

describe("impact.ts calculations", () => {
  describe("hasClearFormula", () => {
    it("returns false for null, undefined, or empty inputs", () => {
      expect(hasClearFormula(null)).toBe(false);
      expect(hasClearFormula(undefined)).toBe(false);
      expect(
        hasClearFormula({
          deductions: [],
          money_basis: null,
          royalty_rate_percent: null,
        }),
      ).toBe(false);
    });

    it("returns true when royalty_rate_percent is present", () => {
      expect(
        hasClearFormula({
          deductions: [],
          money_basis: null,
          royalty_rate_percent: { quote: "15%", value: 15 },
        }),
      ).toBe(true);
    });

    it("returns false when only money_basis is stated (no rate to calculate)", () => {
      expect(
        hasClearFormula({
          deductions: [],
          money_basis: { quote: "net receipts", value: "net" },
          royalty_rate_percent: null,
        }),
      ).toBe(false);
    });

    it("never invents a rate when only deductions are listed", () => {
      const inputs: ImpactInputs = {
        deductions: [{ quote: "recording costs", value: "recording costs" }],
        money_basis: null,
        royalty_rate_percent: null,
      };
      expect(hasClearFormula(inputs)).toBe(false);
    });
  });

  describe("isHighImpactClause", () => {
    const baseClause: ClauseResult = {
      clause_id: "c-1",
      pages: [1],
      original_text: "This agreement is governed by the laws of Kenya.",
      status: "evaluated",
      comparison: "matches_standard",
      headline: "Governing law",
      what_it_says: "Kenyan law applies.",
      what_it_means: "Standard jurisdiction.",
      comparison_note: null,
      impact_inputs: null,
      linked_clauses: [],
      ask_them: null,
      standard_template_id: null,
      standard_excerpt: null,
      evidence: [],
      evidence_ids: [],
      evidence_quote: null,
      provider: null,
      model_version: null,
    };

    it("marks standard boilerplate clauses as low-impact (false)", () => {
      expect(isHighImpactClause(baseClause, "Governing Law")).toBe(false);
      expect(
        isHighImpactClause(
          {
            ...baseClause,
            original_text: "Notices must be in writing and sent to the address above.",
            headline: "Notices",
          },
          "Notices",
        ),
      ).toBe(false);
    });

    it("marks clauses with deviations as high-impact (true)", () => {
      expect(isHighImpactClause({ ...baseClause, comparison: "worse_for_you" })).toBe(true);
      expect(isHighImpactClause({ ...baseClause, comparison: "not_in_standard" })).toBe(true);
      expect(isHighImpactClause({ ...baseClause, comparison: "better_for_you" })).toBe(true);
      expect(isHighImpactClause({ ...baseClause, comparison: "missing_from_contract" })).toBe(true);
    });

    it("marks financial clauses with impact_inputs as high-impact (true)", () => {
      const moneyClause: ClauseResult = {
        ...baseClause,
        impact_inputs: {
          royalty_rate_percent: { quote: "15%", value: 15 },
          money_basis: { quote: "net", value: "net" },
          deductions: [],
        },
      };
      expect(isHighImpactClause(moneyClause)).toBe(true);
    });

    it("marks high-impact topics (royalties, ownership, exclusivity, termination, indemnity) as high-impact even if matches_standard", () => {
      expect(
        isHighImpactClause({
          ...baseClause,
          original_text: "Company pays Artist a royalty of 20% on all net receipts.",
          headline: "Royalties and payment terms",
        }),
      ).toBe(true);

      expect(
        isHighImpactClause({
          ...baseClause,
          original_text: "Artist assigns all master recording copyright to the label.",
          headline: "Assignment of copyright in masters",
        }),
      ).toBe(true);

      expect(
        isHighImpactClause({
          ...baseClause,
          original_text: "Artist shall not perform for any competing brand for 6 months post-term.",
          headline: "Post-term exclusivity restriction",
        }),
      ).toBe(true);

      expect(
        isHighImpactClause({
          ...baseClause,
          original_text: "Either party may terminate upon 30 days notice for material breach.",
          headline: "Termination for breach",
        }),
      ).toBe(true);

      expect(
        isHighImpactClause({
          ...baseClause,
          original_text: "Artist indemnifies the company against all third-party claims.",
          headline: "Indemnity and warranties",
        }),
      ).toBe(true);
    });

    it("marks clauses involved in contract-wide issues as high-impact (true)", () => {
      expect(isHighImpactClause(baseClause, "Governing Law", true)).toBe(true);
    });
  });
});
