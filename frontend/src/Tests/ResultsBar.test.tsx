import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ResultsBar } from "@/components/results/ResultsBar";

describe("ResultsBar", () => {
  it("renders download report action button", () => {
    const html = renderToStaticMarkup(<ResultsBar onOpenReport={vi.fn()} />);
    expect(html).toContain("📄 Download Report");
    expect(html).toContain('data-testid="download-report-btn"');
  });
});
