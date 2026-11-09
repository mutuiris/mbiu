import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ReportChecklist } from "@/components/results/ReportChecklist";

describe("ReportChecklist", () => {
  it("renders checklist items with checkboxes and note lines", () => {
    const html = renderToStaticMarkup(
      <ReportChecklist
        questions={[
          "Can we clarify the reversion term?",
          "Can we cap expenses at 15%?",
        ]}
      />
    );

    expect(html).toContain("6. Numbered Negotiation Checklist");
    expect(html).toContain("Can we clarify the reversion term?");
    expect(html).toContain("Can we cap expenses at 15%?");
    expect(html).toContain("Notes: ____________________");
    expect(html).toContain("Agreed: ____________________");
  });
});
