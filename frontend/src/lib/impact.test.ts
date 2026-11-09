import { describe, expect, it } from "vitest";
import {
  EXAMPLE_GROSS,
  shillingSteps,
  formatShillings,
  hasClearFormula,
  isHighImpactClause,
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
      expect(shillingSteps(inputs, 1_000_000)).toBeNull();
    });
  });

  describe("formatShillings", () => {
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


describe("shillingSteps", () => {
  const inputs04: ImpactInputs = {
    royalty_rate_percent: null,
    money_basis: null,
    deductions: [
      { value: "15% free goods allowance", quote: "the Free Goods Allowance of fifteen percent (15%)" },
      { value: "Container and Infrastructure Charge", quote: "Container and Infrastructure Charge" },
    ],
  };

  it("applies only percentages the contract quotes, in order", () => {
    const s = shillingSteps(inputs04, 1_000_000)!;
    expect(s.steps.map((x) => [x.percent, x.amount])).toEqual([
      [15, 150_000],
      [null, null],
    ]);
    expect(s.base).toBe(850_000);
    expect(s.ratePercent).toBeNull();
    expect(s.youReceive).toBeNull();
  });

  it("flags that the base is a ceiling when a deduction has no stated amount", () => {
    expect(shillingSteps(inputs04, 1_000_000)!.baseIsCeiling).toBe(true);
    const allStated = shillingSteps({ ...inputs04, deductions: [inputs04.deductions[0]] }, 1_000_000)!;
    expect(allStated.baseIsCeiling).toBe(false);
  });

  it("adds You receive only with a quoted rate", () => {
    const s = shillingSteps(
      { ...inputs04, royalty_rate_percent: { value: 12, quote: "twelve percent (12%)" } },
      1_000_000,
    )!;
    expect(s.youReceive).toBe(102_000);
    expect(s.ratePhrase).toBe("twelve percent (12%)");
  });

  it("returns null when nothing is quoted as a number", () => {
    expect(
      shillingSteps(
        { royalty_rate_percent: null, money_basis: null, deductions: [{ value: "Container charge", quote: "Container charge" }] },
        1_000_000,
      ),
    ).toBeNull();
    expect(shillingSteps(null, 1_000_000)).toBeNull();
  });

  it("never goes below zero and rounds to whole shillings", () => {
    const s = shillingSteps(
      {
        royalty_rate_percent: null,
        money_basis: null,
        deductions: [
          { value: "60%", quote: "60%" },
          { value: "70%", quote: "70%" },
        ],
      },
      333,
    )!;
    expect(s.base).toBe(40);
    expect(Number.isInteger(s.steps[0].amount!)).toBe(true);
  });

  it("starts from a one-million-shilling example", () => {
    expect(EXAMPLE_GROSS).toBe(1_000_000);
  });
});
