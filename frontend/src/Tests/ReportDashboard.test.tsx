import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ReportDashboard } from "@/components/results/ReportDashboard";

describe("ReportDashboard", () => {
  it("renders tally counts, meta counts, and priority questions", () => {
    const html = renderToStaticMarkup(
      <ReportDashboard
        labelCounts={{
          typical: 5,
          unusual: 2,
          worth_asking_about: 4,
          cannot_compare: 1,
        }}
        issuesCount={2}
        missingProtectionsCount={3}
        topAsks={[{ question: "Can we cap deductions?" }]}
      />
    );

    expect(html).toContain("2. Executive Summary Dashboard");
    expect(html).toContain("Typical");
    expect(html).toContain("5");
    expect(html).toContain("Worth Asking About");
    expect(html).toContain("4");
    expect(html).toContain("Contract-wide contradictions or overrides:</strong> 2");
    expect(html).toContain("“Can we cap deductions?”");
  });
});
