import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ReportGuide } from "@/components/results/ReportGuide";

describe("ReportGuide", () => {
  it("renders objective label definitions table", () => {
    const html = renderToStaticMarkup(<ReportGuide />);

    expect(html).toContain("1. How to Read This Report");
    expect(html).toContain("Typical does not mean safe");
    expect(html).toContain("[TYPICAL]");
    expect(html).toContain("[UNUSUAL]");
    expect(html).toContain("[WORTH ASKING ABOUT]");
    expect(html).toContain("[COULDN&#x27;T COMPARE]");
  });
});
