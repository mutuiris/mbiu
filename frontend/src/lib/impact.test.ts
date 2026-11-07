import { describe, expect, it } from "vitest";
import {
  calculateImpact,
  formatShillings,
  hasClearFormula,
  isHighImpactClause,
  DEFAULT_EXAMPLE_DEDUCTIONS,
} from "./impact";
import type { ClauseResult, ImpactInputs } from "./api/generated/types.gen";

describe("impact.ts calculations in shillings", () => {
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
      expect(calculateImpact(inputs)).toBeNull();
    });
  });

  describe("gross vs net calculations", () => {
    it("calculates gross basis royalties where deductions do not reduce artist payout", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "20%", value: 20 },
        money_basis: { quote: "gross revenue", value: "gross" },
        deductions: [{ quote: "marketing", value: "marketing" }],
      };

      const result = calculateImpact(inputs, 100_000, 30_000);
      expect(result).not.toBeNull();
      // On Gross: 20% of 100,000 = 20,000 KES
      expect(result?.basis).toBe("gross");
      expect(result?.artistEarnings).toBe(20_000);
      expect(result?.earningsUnderGross).toBe(20_000);
      // If it had been net: 20% of (100,000 - 30,000 = 70,000) = 14,000 KES
      expect(result?.earningsUnderNet).toBe(14_000);
      expect(result?.lossToDeductions).toBe(6_000);
    });

    it("calculates net basis royalties where deductions reduce payout before percentage applies", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "15%", value: 15 },
        money_basis: { quote: "net revenue", value: "net" },
        deductions: [{ quote: "recording expenses", value: "recording" }],
      };

      const result = calculateImpact(inputs, 100_000, 40_000);
      expect(result).not.toBeNull();
      // Net basis: 100,000 - 40,000 = 60,000 net revenue
      expect(result?.netRevenue).toBe(60_000);
      // Artist gets 15% of 60,000 = 9,000 KES
      expect(result?.artistEarnings).toBe(9_000);
      expect(result?.earningsUnderNet).toBe(9_000);
      // Under Gross: 15% of 100,000 = 15,000 KES
      expect(result?.earningsUnderGross).toBe(15_000);
      // Loss to deductions: 15,000 - 9,000 = 6,000 KES
      expect(result?.lossToDeductions).toBe(6_000);
    });
  });

  describe("deductions before royalties", () => {
    it("handles deductions exceeding gross revenue without negative payout", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "12%", value: 12 },
        money_basis: { quote: "net receipts", value: "net" },
        deductions: [
          { quote: "marketing", value: "marketing" },
          { quote: "tour support", value: "tour support" },
        ],
      };

      // Deductions (150,000) exceed Gross (100,000)
      const result = calculateImpact(inputs, 100_000, 150_000);
      expect(result).not.toBeNull();
      expect(result?.netRevenue).toBe(0);
      expect(result?.artistEarnings).toBe(0);
      expect(result?.earningsUnderNet).toBe(0);
      expect(result?.earningsUnderGross).toBe(12_000);
      expect(result?.lossToDeductions).toBe(12_000);
    });

    it("uses default example deductions when deductions exist but custom amount is not passed", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "10%", value: 10 },
        money_basis: { quote: "net", value: "net" },
        deductions: [{ quote: "video production", value: "video production" }],
      };

      const result = calculateImpact(inputs, 100_000);
      expect(result).not.toBeNull();
      expect(result?.totalDeductions).toBe(DEFAULT_EXAMPLE_DEDUCTIONS);
      expect(result?.netRevenue).toBe(100_000 - DEFAULT_EXAMPLE_DEDUCTIONS);
    });
  });

  describe("zero and very large values", () => {
    it("handles zero gross revenue gracefully", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "15%", value: 15 },
        money_basis: { quote: "net", value: "net" },
        deductions: [{ quote: "packaging", value: "packaging" }],
      };

      const result = calculateImpact(inputs, 0, 10_000);
      expect(result).not.toBeNull();
      expect(result?.revenueGross).toBe(0);
      expect(result?.netRevenue).toBe(0);
      expect(result?.artistEarnings).toBe(0);
      expect(result?.earningsUnderGross).toBe(0);
      expect(result?.earningsUnderNet).toBe(0);
      expect(result?.lossToDeductions).toBe(0);
    });

    it("handles zero percent royalty rate", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "0%", value: 0 },
        money_basis: { quote: "gross", value: "gross" },
        deductions: [],
      };

      const result = calculateImpact(inputs, 100_000, 0);
      expect(result).not.toBeNull();
      expect(result?.artistEarnings).toBe(0);
      expect(result?.lossToDeductions).toBe(0);
    });

    it("handles zero deductions cleanly", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "18%", value: 18 },
        money_basis: { quote: "net", value: "net" },
        deductions: [],
      };

      const result = calculateImpact(inputs, 100_000, 0);
      expect(result).not.toBeNull();
      expect(result?.totalDeductions).toBe(0);
      expect(result?.artistEarnings).toBe(18_000);
      expect(result?.earningsUnderGross).toBe(18_000);
      expect(result?.lossToDeductions).toBe(0);
    });

    it("handles very large values in billions without overflow or NaN", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "16.5%", value: 16.5 },
        money_basis: { quote: "net", value: "net" },
        deductions: [{ quote: "global marketing", value: "marketing" }],
      };

      const grossOneBillion = 1_000_000_000;
      const deductionsTwoHundredMillion = 200_000_000;

      const result = calculateImpact(inputs, grossOneBillion, deductionsTwoHundredMillion);
      expect(result).not.toBeNull();
      expect(result?.revenueGross).toBe(1_000_000_000);
      expect(result?.netRevenue).toBe(800_000_000);
      // 16.5% of 800,000,000 = 132,000,000
      expect(result?.artistEarnings).toBe(132_000_000);
      // Gross: 16.5% of 1,000,000,000 = 165,000,000
      expect(result?.earningsUnderGross).toBe(165_000_000);
      expect(result?.lossToDeductions).toBe(33_000_000);
      expect(Number.isFinite(result?.artistEarnings)).toBe(true);
    });

    it("handles negative or non-finite inputs by clamping safely", () => {
      const inputs: ImpactInputs = {
        royalty_rate_percent: { quote: "10%", value: 10 },
        money_basis: { quote: "net", value: "net" },
        deductions: [],
      };

      const result = calculateImpact(inputs, -50_000, -10_000);
      expect(result).not.toBeNull();
      expect(result?.revenueGross).toBe(0);
      expect(result?.totalDeductions).toBe(0);
      expect(result?.artistEarnings).toBe(0);
    });
  });

  describe("rounding to whole shillings", () => {
    it("strictly rounds fractions of shillings to whole integers", () => {
      const inputs: ImpactInputs = {
        // 13.333% royalty
        royalty_rate_percent: { quote: "13.333%", value: 13.333 },
        money_basis: { quote: "net", value: "net" },
        deductions: [{ quote: "costs", value: "costs" }],
      };

      // Gross 77,777 KES, Deductions 23,456 KES => Net 54,321 KES
      // 54,321 * 0.13333 = 7242.61893 => rounded to 7243
      const result = calculateImpact(inputs, 77_777, 23_456);
      expect(result).not.toBeNull();
      expect(Number.isInteger(result?.artistEarnings)).toBe(true);
      expect(Number.isInteger(result?.earningsUnderGross)).toBe(true);
      expect(Number.isInteger(result?.earningsUnderNet)).toBe(true);
      expect(Number.isInteger(result?.lossToDeductions)).toBe(true);
      expect(result?.artistEarnings).toBe(Math.round(54_321 * 0.13333));
    });

    it("formatShillings rounds to whole integer currency string", () => {
      expect(formatShillings(15000.4)).toBe("KES 15,000");
      expect(formatShillings(15000.7)).toBe("KES 15,001");
      expect(formatShillings(0)).toBe("KES 0");
      expect(formatShillings(-0)).toBe("KES 0");
      expect(formatShillings(NaN)).toBe("KES 0");
      expect(formatShillings(1_000_000)).toBe("KES 1,000,000");
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
      fairer_wording: null,
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

