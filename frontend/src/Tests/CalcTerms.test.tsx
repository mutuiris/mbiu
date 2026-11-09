import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CalcTerms } from "@/components/results/CalcTerms";

describe("CalcTerms", () => {
  it("renders royalty rate, basis badge and deduction quotes", () => {
    const html = renderToStaticMarkup(
      <CalcTerms
        royaltyRate={15}
        quotedRateText="15% royalty"
        isNet={true}
        quotedBasisText="Net Receipts"
        deductionQuotes={["recording costs", "marketing"]}
      />
    );

    expect(html).toContain("15%");
    expect(html).toContain("(from “15% royalty”)");
    expect(html).toContain("Net (Deductions taken first)");
    expect(html).toContain("“recording costs”");
    expect(html).toContain("“marketing”");
  });

  it("renders gross basis badge when isNet is false", () => {
    const html = renderToStaticMarkup(
      <CalcTerms
        royaltyRate={20}
        isNet={false}
        deductionQuotes={[]}
      />
    );

    expect(html).toContain("20%");
    expect(html).toContain("Gross (Calculated before deductions)");
  });
});
