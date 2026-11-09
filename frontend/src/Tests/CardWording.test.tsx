import React from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CardWording } from "@/components/results/CardWording";

describe("CardWording", () => {
  it("renders collapsible exact wording details block with original text and standard excerpt", () => {
    const html = renderToStaticMarkup(
      <CardWording
        originalText="Company retains master rights in perpetuity."
        standardExcerpt="Standard reversion term is 5-7 years."
      />
    );

    expect(html).toContain("Show exact wording");
    expect(html).toContain("Company retains master rights in perpetuity.");
    expect(html).toContain("Reviewed template excerpt:");
    expect(html).toContain("Standard reversion term is 5-7 years.");
  });

  it("omits standard excerpt block when not provided", () => {
    const html = renderToStaticMarkup(
      <CardWording originalText="Direct unaltered text." />
    );

    expect(html).toContain("Direct unaltered text.");
    expect(html).not.toContain("Reviewed template excerpt:");
  });
});
