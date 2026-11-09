import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { ImpactInputs } from "@/lib/api/generated/types.gen";

import { ShillingsCalculator } from "./ShillingsCalculator";

const inputs04: ImpactInputs = {
  royalty_rate_percent: null,
  money_basis: null,
  deductions: [
    { value: "15% free goods allowance", quote: "the Free Goods Allowance of fifteen percent (15%)" },
    { value: "Container and Infrastructure Charge", quote: "Container and Infrastructure Charge" },
  ],
};

describe("ShillingsCalculator", () => {
  it("walks through the quoted deductions from an example amount", () => {
    const html = renderToStaticMarkup(<ShillingsCalculator inputs={inputs04} />);
    expect(html).toContain("If the label receives");
    expect(html).toContain("Example figures, change them");
    expect(html).toContain("15%");
    expect(html).toContain("“the Free Goods Allowance of fifteen percent (15%)”");
    expect(html).toContain("KES 150,000");
    expect(html).toContain("At most, the amount your royalty is worked out on");
    expect(html).toContain("KES 850,000");
    expect(html).toContain("less, because one charge has no stated amount");
    expect(html).toContain("tabular-nums");
  });

  it("never invents a royalty rate", () => {
    expect(renderToStaticMarkup(<ShillingsCalculator inputs={inputs04} />)).not.toContain("You receive");
  });

  it("shows what you receive when the contract states the rate", () => {
    const html = renderToStaticMarkup(
      <ShillingsCalculator inputs={{ ...inputs04, royalty_rate_percent: { value: 12, quote: "twelve percent (12%)" } }} />,
    );
    expect(html).toContain("At most, you receive at the contract&#x27;s 12% royalty");
    expect(html).toContain("KES 102,000");
  });

  it("lists a deduction without a stated amount honestly", () => {
    const html = renderToStaticMarkup(<ShillingsCalculator inputs={inputs04} />);
    expect(html).toContain("Container and Infrastructure Charge");
    expect(html).toContain("Amount not stated here");
  });

  it("states a definite figure when every deduction has an amount", () => {
    const html = renderToStaticMarkup(<ShillingsCalculator inputs={{ ...inputs04, deductions: [inputs04.deductions[0]] }} />);
    expect(html).toContain("The amount your royalty is worked out on");
    expect(html).not.toContain("At most");
  });

  it("renders nothing when no figure is quoted", () => {
    expect(
      renderToStaticMarkup(
        <ShillingsCalculator inputs={{ royalty_rate_percent: null, money_basis: null, deductions: [{ value: "fees", quote: "fees" }] }} />,
      ),
    ).toBe("");
    expect(renderToStaticMarkup(<ShillingsCalculator inputs={null} />)).toBe("");
  });
});
