import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ReportToolbar } from "@/components/results/ReportToolbar";

describe("ReportToolbar", () => {
  it("renders print and close buttons with toolbar title", () => {
    const html = renderToStaticMarkup(
      <ReportToolbar onPrint={vi.fn()} onClose={vi.fn()} />
    );

    expect(html).toContain("Evaluation Report Preview");
    expect(html).toContain("🖨️ Print / Save as PDF");
    expect(html).toContain("✕ Close");
  });
});
