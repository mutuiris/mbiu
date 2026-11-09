import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CalcBreakdown } from "@/components/results/CalcBreakdown";

describe("CalcBreakdown", () => {
  it("renders artist calculated earnings, net comparison, and reset button", () => {
    const html = renderToStaticMarkup(
      <CalcBreakdown
        artistEarnings={12000}
        isNet={true}
        earningsUnderGross={18000}
        lossToDeductions={6000}
        onReset={vi.fn()}
      />
    );

    expect(html).toContain("Your calculated earnings:");
    expect(html).toContain("KES 12,000");
    expect(html).toContain("If calculated on Gross:");
    expect(html).toContain("KES 18,000");
    expect(html).toContain("Loss to deductions:");
    expect(html).toContain("−KES 6,000");
    expect(html).toContain("Reset example figures");
  });

  it("omits net comparison when isNet is false", () => {
    const html = renderToStaticMarkup(
      <CalcBreakdown
        artistEarnings={20000}
        isNet={false}
        earningsUnderGross={20000}
        lossToDeductions={0}
        onReset={vi.fn()}
      />
    );

    expect(html).toContain("KES 20,000");
    expect(html).not.toContain("Loss to deductions:");
  });
});
