import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CalcInputs } from "@/components/results/CalcInputs";

describe("CalcInputs", () => {
  it("renders gross revenue input and current formatted value", () => {
    const html = renderToStaticMarkup(
      <CalcInputs
        grossInput={100000}
        deductionsInput={0}
        hasDeductions={false}
        onGrossChange={vi.fn()}
        onDeductionsChange={vi.fn()}
      />
    );

    expect(html).toContain("Example gross revenue (KES)");
    expect(html).toContain("Current: KES 100,000");
    expect(html).not.toContain("Example deductions before royalties (KES)");
  });

  it("renders deductions input when hasDeductions is true", () => {
    const html = renderToStaticMarkup(
      <CalcInputs
        grossInput={200000}
        deductionsInput={50000}
        hasDeductions={true}
        onGrossChange={vi.fn()}
        onDeductionsChange={vi.fn()}
      />
    );

    expect(html).toContain("Example deductions before royalties (KES)");
    expect(html).toContain("Current: KES 50,000");
  });
});
