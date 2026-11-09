import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ReportCover } from "@/components/results/ReportCover";

describe("ReportCover", () => {
  it("renders report title, metadata grid and legal disclaimer", () => {
    const html = renderToStaticMarkup(
      <ReportCover
        currentDate="November 9, 2026"
        pageCount={4}
        totalClauses={12}
        isStreaming={false}
        evaluatedCount={12}
      />
    );

    expect(html).toContain("MBIU CONTRACT EVALUATION REPORT");
    expect(html).toContain("4 pages · 12 total clauses");
    expect(html).toContain("Completed (12 clauses evaluated)");
    expect(html).toContain("IMPORTANT NOTICE:");
  });
});
